"""Receipt vision endpoints — preview and confirm sales receipt images."""

import base64
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import SalesLog, get_db
from services.claude import parse_image_with_claude, strip_fences
from services.receipt import fuzzy_match_recipe, process_receipt_items

router = APIRouter()

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_RECEIPT_EXTRACTION_PROMPT = (
    "You are a data extraction assistant for a restaurant POS system. "
    "Examine the sales receipt or closing report image and return ONLY a single valid JSON object. "
    "Do not include markdown fences, explanations, or any other text. "
    'The JSON must have this exact structure:\n'
    '{"sale_date": "<YYYY-MM-DD or null>", "items": [{"name": "<menu item name>", '
    '"quantity": <integer>, "unit_price": <number or null>, "total_price": <number or null>}]}\n'
    "Normalise menu item names to lowercase English. Quantities must be positive integers."
)


class ReceiptLineItem(BaseModel):
    name: str
    quantity: int
    unit_price: Optional[float] = None
    total_price: Optional[float] = None


class ReceiptParseResult(BaseModel):
    sale_date: Optional[str] = None
    items: list[ReceiptLineItem] = Field(default_factory=list)


class SuggestedMatch(BaseModel):
    id: int
    name: str
    ingredient_count: int


class PreviewItem(BaseModel):
    name: str
    quantity: int
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    suggested_match: Optional[SuggestedMatch] = None
    match_score: float = 0.0


class PreviewResponse(BaseModel):
    sale_date: Optional[str]
    duplicate_warning: bool
    items: list[PreviewItem]


class ConfirmItem(BaseModel):
    name: str
    quantity: int
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    recipe_id: Optional[int] = None
    include: bool = True


class ConfirmRequest(BaseModel):
    sale_date: Optional[str] = None
    items: list[ConfirmItem]


class ResultItem(BaseModel):
    name: str
    quantity: int
    total_price: Optional[float]
    recipe_id: int
    sales_log_id: int
    ingredients_deducted: int


class ConfirmResponse(BaseModel):
    sale_date: Optional[str]
    items_processed: int
    items_skipped: int
    items: list[ResultItem]


def _parse_receipt_json(raw: str) -> ReceiptParseResult:
    cleaned = strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned non-JSON: {exc}") from exc
    try:
        return ReceiptParseResult(
            sale_date=data.get("sale_date"),
            items=[ReceiptLineItem(**i) for i in data.get("items", [])],
        )
    except Exception as exc:
        raise ValueError(f"Invalid receipt structure: {exc}") from exc


@router.post("/preview", response_model=PreviewResponse)
async def preview_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PreviewResponse:
    """Parse receipt image, return items with fuzzy recipe match suggestions. No DB writes."""
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        raw_text = parse_image_with_claude(
            image_base64=base64.b64encode(raw_bytes).decode("ascii"),
            prompt=_RECEIPT_EXTRACTION_PROMPT,
            media_type=file.content_type,
            max_tokens=2048,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        parsed = _parse_receipt_json(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    duplicate_warning = False
    if parsed.sale_date:
        try:
            sale_dt = datetime.strptime(parsed.sale_date, "%Y-%m-%d")
            duplicate_warning = (
                db.query(SalesLog)
                .filter(
                    SalesLog.sold_at >= sale_dt.replace(hour=0, minute=0, second=0),
                    SalesLog.sold_at < sale_dt.replace(hour=23, minute=59, second=59),
                )
                .first()
                is not None
            )
        except ValueError:
            pass

    preview_items = []
    for item in parsed.items:
        recipe, score = fuzzy_match_recipe(db, item.name)
        suggested = None
        if recipe:
            suggested = SuggestedMatch(
                id=recipe.id,
                name=recipe.name,
                ingredient_count=len(recipe.ingredient_links),
            )
        preview_items.append(
            PreviewItem(
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                suggested_match=suggested,
                match_score=round(score, 2),
            )
        )

    return PreviewResponse(
        sale_date=parsed.sale_date,
        duplicate_warning=duplicate_warning,
        items=preview_items,
    )


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_receipt(
    body: ConfirmRequest,
    db: Session = Depends(get_db),
) -> ConfirmResponse:
    """Persist user-reviewed sales data: create SalesLogs and deduct ingredient stock."""
    included = [item for item in body.items if item.include]

    if not included:
        return ConfirmResponse(
            sale_date=body.sale_date,
            items_processed=0,
            items_skipped=len(body.items),
            items=[],
        )

    item_dicts = [item.model_dump() for item in included]
    results, skipped_count = process_receipt_items(item_dicts, body.sale_date, db)
    skipped_count += len(body.items) - len(included)
    db.commit()

    return ConfirmResponse(
        sale_date=body.sale_date,
        items_processed=len(results),
        items_skipped=skipped_count,
        items=[ResultItem(**r) for r in results],
    )
