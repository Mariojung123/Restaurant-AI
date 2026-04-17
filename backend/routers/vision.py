"""
Vision endpoints.

Accepts an uploaded image (e.g. an invoice or delivery receipt) and asks
Claude Vision to extract structured information. Downstream parsing of the
text into inventory logs will be wired up as the product evolves.
"""

import base64
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from services.claude import parse_image_with_claude


router = APIRouter()


DEFAULT_EXTRACTION_PROMPT = (
    "This is a restaurant purchase invoice or delivery receipt. "
    "Extract each line item as JSON with fields: name, quantity, unit, unit_price, total_price. "
    "Also return supplier name and invoice date if visible. Respond with JSON only."
)


class VisionResponse(BaseModel):
    """Plain-text extraction result returned by Claude Vision."""

    result: str


@router.post("/parse", response_model=VisionResponse)
async def parse_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
) -> VisionResponse:
    """Parse an uploaded image using Claude Vision and return the raw reply."""
    if file.content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
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
