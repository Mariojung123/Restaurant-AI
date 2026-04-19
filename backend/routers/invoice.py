"""Invoice vision endpoints — parse, preview, and confirm invoice images."""

import base64
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import InventoryLog, get_db
from services.claude import parse_image_with_claude, strip_fences
from services.invoice import fuzzy_match_ingredient, process_invoice_items

router = APIRouter()

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_INVOICE_EXTRACTION_PROMPT = (
    "You are a data extraction assistant for a restaurant inventory system. "
    "Examine the invoice or delivery receipt image and return ONLY a single valid JSON object. "
    "Do not include markdown fences, explanations, or any other text. "
    'The JSON must have this exact structure:\n'
    '{"supplier_name": "<string or null>", "invoice_date": "<YYYY-MM-DD or null>", '
    '"items": [{"name": "<ingredient name>", "quantity": <number>, "unit": "<unit>", '
    '"unit_price": <number or null>, "total_price": <number or null>}]}\n'
    "Normalise ingredient names to lowercase English. Quantities must be positive numbers."
)


class InvoiceLineItem(BaseModel):
    name: str
    quantity: float
    unit: str
    unit_price: Optional[float] = None
    total_price: Optional[float] = None


class InvoiceParseResult(BaseModel):
    supplier_name: Optional[str] = None
    invoice_date: Optional[str] = None
    items: list[InvoiceLineItem] = Field(default_factory=list)


class ProcessedItem(BaseModel):
    name: str
    quantity: float
    unit: str
    unit_price: Optional[float]
    action: str
    ingredient_id: int
    inventory_log_id: int


class InvoiceResponse(BaseModel):
    supplier: Optional[str]
    invoice_date: Optional[str]
    items_processed: int
    items: list[ProcessedItem]


class SuggestedMatch(BaseModel):
    id: int
    name: str
    unit: str


class PreviewItem(BaseModel):
    name: str
    quantity: float
    unit: str
    unit_price: Optional[float] = None
    suggested_match: Optional[SuggestedMatch] = None
    match_score: float = 0.0


class PreviewResponse(BaseModel):
    supplier: Optional[str]
    invoice_date: Optional[str]
    duplicate_warning: bool
    items: list[PreviewItem]


class ConfirmItem(BaseModel):
    name: str
    quantity: float
    unit: str
    unit_price: Optional[float] = None
    ingredient_id: Optional[int] = None
    include: bool = True


class ConfirmRequest(BaseModel):
    supplier: Optional[str] = None
    invoice_date: Optional[str] = None
    items: list[ConfirmItem]


def _parse_invoice_json(raw: str) -> InvoiceParseResult:
    cleaned = strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned non-JSON: {exc}") from exc
    try:
        return InvoiceParseResult(
            supplier_name=data.get("supplier_name"),
            invoice_date=data.get("invoice_date"),
            items=[InvoiceLineItem(**i) for i in data.get("items", [])],
        )
    except Exception as exc:
        raise ValueError(f"Invalid invoice structure: {exc}") from exc


def _read_and_encode(file_bytes: bytes) -> str:
    return base64.b64encode(file_bytes).decode("ascii")


@router.post("/preview", response_model=PreviewResponse)
async def preview_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PreviewResponse:
    """Parse invoice image, return items with fuzzy match suggestions. No DB writes."""
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        raw_text = parse_image_with_claude(
            image_base64=_read_and_encode(raw_bytes),
            prompt=_INVOICE_EXTRACTION_PROMPT,
            media_type=file.content_type,
            max_tokens=2048,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        parsed = _parse_invoice_json(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    duplicate_warning = False
    if parsed.supplier_name and parsed.invoice_date:
        duplicate_warning = (
            db.query(InventoryLog)
            .filter(
                InventoryLog.supplier == parsed.supplier_name,
                InventoryLog.note == "Auto-created from invoice scan",
            )
            .first()
            is not None
        )

    preview_items = []
    for item in parsed.items:
        ingredient, score = fuzzy_match_ingredient(db, item.name)
        suggested = None
        if ingredient:
            suggested = SuggestedMatch(id=ingredient.id, name=ingredient.name, unit=ingredient.unit)
        preview_items.append(
            PreviewItem(
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                suggested_match=suggested,
                match_score=round(score, 2),
            )
        )

    return PreviewResponse(
        supplier=parsed.supplier_name,
        invoice_date=parsed.invoice_date,
        duplicate_warning=duplicate_warning,
        items=preview_items,
    )


@router.post("/confirm", response_model=InvoiceResponse)
async def confirm_invoice(
    body: ConfirmRequest,
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    """Persist user-reviewed invoice items to DB."""
    included = [item for item in body.items if item.include]

    if not included:
        return InvoiceResponse(
            supplier=body.supplier,
            invoice_date=body.invoice_date,
            items_processed=0,
            items=[],
        )

    item_dicts = [item.model_dump() for item in included]
    processed = process_invoice_items(item_dicts, body.supplier, db)
    db.commit()

    return InvoiceResponse(
        supplier=body.supplier,
        invoice_date=body.invoice_date,
        items_processed=len(processed),
        items=[ProcessedItem(**p) for p in processed],
    )


@router.post("/", response_model=InvoiceResponse)
async def process_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    """Parse an invoice image and auto-update inventory (no preview step)."""
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        raw_text = parse_image_with_claude(
            image_base64=_read_and_encode(raw_bytes),
            prompt=_INVOICE_EXTRACTION_PROMPT,
            media_type=file.content_type,
            max_tokens=2048,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        parsed = _parse_invoice_json(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not parsed.items:
        return InvoiceResponse(
            supplier=parsed.supplier_name,
            invoice_date=parsed.invoice_date,
            items_processed=0,
            items=[],
        )

    item_dicts = [item.model_dump() for item in parsed.items]
    processed = process_invoice_items(item_dicts, parsed.supplier_name, db)
    db.commit()

    return InvoiceResponse(
        supplier=parsed.supplier_name,
        invoice_date=parsed.invoice_date,
        items_processed=len(processed),
        items=[ProcessedItem(**p) for p in processed],
    )
