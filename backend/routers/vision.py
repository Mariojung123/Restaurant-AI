"""
Vision endpoints.

Accepts uploaded invoice/receipt images and uses Claude Vision to extract
structured data. /parse returns raw text; /invoice auto-updates inventory.
"""

import base64
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from services.claude import parse_image_with_claude
from services.invoice import process_invoice_items


router = APIRouter()

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

DEFAULT_EXTRACTION_PROMPT = (
    "This is a restaurant purchase invoice or delivery receipt. "
    "Extract each line item as JSON with fields: name, quantity, unit, unit_price, total_price. "
    "Also return supplier name and invoice date if visible. Respond with JSON only."
)

INVOICE_EXTRACTION_PROMPT = (
    "You are a data extraction assistant for a restaurant inventory system. "
    "Examine the invoice or delivery receipt image and return ONLY a single valid JSON object. "
    "Do not include markdown fences, explanations, or any other text. "
    'The JSON must have this exact structure:\n'
    '{"supplier_name": "<string or null>", "invoice_date": "<YYYY-MM-DD or null>", '
    '"items": [{"name": "<ingredient name>", "quantity": <number>, "unit": "<unit>", '
    '"unit_price": <number or null>, "total_price": <number or null>}]}\n'
    "Normalise ingredient names to lowercase English. Quantities must be positive numbers."
)


class VisionResponse(BaseModel):
    result: str


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


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return raw.strip()


def _parse_invoice_json(raw: str) -> InvoiceParseResult:
    cleaned = _strip_fences(raw)
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


@router.post("/parse", response_model=VisionResponse)
async def parse_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
) -> VisionResponse:
    """Parse an uploaded image using Claude Vision and return the raw reply."""
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    image_base64 = base64.b64encode(raw).decode("ascii")

    try:
        result = parse_image_with_claude(
            image_base64=image_base64,
            prompt=prompt or DEFAULT_EXTRACTION_PROMPT,
            media_type=file.content_type,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return VisionResponse(result=result)


@router.post("/invoice", response_model=InvoiceResponse)
async def process_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    """Parse an invoice image and auto-update inventory.

    Matches each line item to an existing Ingredient (case-insensitive) or
    creates a new one, then records an InventoryLog and increments stock.
    """
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}",
        )

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    image_base64 = base64.b64encode(raw_bytes).decode("ascii")

    try:
        raw_text = parse_image_with_claude(
            image_base64=image_base64,
            prompt=INVOICE_EXTRACTION_PROMPT,
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
