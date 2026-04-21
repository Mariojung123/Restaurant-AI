"""Invoice vision endpoints — parse, preview, and confirm invoice images."""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import InventoryLog, get_db
from services.constants import AUTO_INVOICE_NOTE
from services.invoice import fuzzy_match_ingredient, process_invoice_items
from services.vision_common import call_vision_api, parse_vision_json, read_upload_file

router = APIRouter()

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


def _parse_invoice_or_422(raw_text: str) -> InvoiceParseResult:
    try:
        return parse_vision_json(raw_text, InvoiceParseResult, "invoice")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _process_invoice_or_422(
    item_dicts: list[dict], supplier: Optional[str], db: Session
) -> list[dict]:
    try:
        return process_invoice_items(item_dicts, supplier, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@router.post("/preview", response_model=PreviewResponse)
async def preview_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PreviewResponse:
    """Parse invoice image, return items with fuzzy match suggestions. No DB writes."""
    raw_bytes = await read_upload_file(file)
    raw_text = call_vision_api(raw_bytes, file.content_type, _INVOICE_EXTRACTION_PROMPT)
    parsed = _parse_invoice_or_422(raw_text)

    duplicate_warning = False
    if parsed.supplier_name and parsed.invoice_date:
        duplicate_warning = (
            db.query(InventoryLog)
            .filter(
                InventoryLog.supplier == parsed.supplier_name,
                    InventoryLog.note == AUTO_INVOICE_NOTE,
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
    processed = _process_invoice_or_422(item_dicts, body.supplier, db)
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
    raw_bytes = await read_upload_file(file)
    raw_text = call_vision_api(raw_bytes, file.content_type, _INVOICE_EXTRACTION_PROMPT)
    parsed = _parse_invoice_or_422(raw_text)

    if not parsed.items:
        return InvoiceResponse(
            supplier=parsed.supplier_name,
            invoice_date=parsed.invoice_date,
            items_processed=0,
            items=[],
        )

    item_dicts = [item.model_dump() for item in parsed.items]
    processed = _process_invoice_or_422(item_dicts, parsed.supplier_name, db)
    db.commit()

    return InvoiceResponse(
        supplier=parsed.supplier_name,
        invoice_date=parsed.invoice_date,
        items_processed=len(processed),
        items=[ProcessedItem(**p) for p in processed],
    )
