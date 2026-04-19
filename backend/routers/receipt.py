"""Receipt vision endpoints — preview and confirm sales receipt images."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from models.database import SalesLog, get_db
from services.receipt import fuzzy_match_recipe, process_receipt_items
from services.vision_common import call_vision_api, parse_vision_json, read_upload_file

router = APIRouter()

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



@router.post("/preview", response_model=PreviewResponse)
async def preview_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PreviewResponse:
    """Parse receipt image, return items with fuzzy recipe match suggestions. No DB writes."""
    raw_bytes = await read_upload_file(file)
    raw_text = call_vision_api(raw_bytes, file.content_type, _RECEIPT_EXTRACTION_PROMPT)
    try:
        parsed = parse_vision_json(raw_text, ReceiptParseResult, "receipt")
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
            logger.warning("Invalid sale_date format '%s', skipping duplicate check", parsed.sale_date)

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
