"""Generic vision endpoint — raw image-to-text extraction."""

import base64
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from services.constants import ALLOWED_IMAGE_TYPES
from services.claude import parse_image_with_claude

router = APIRouter()

_DEFAULT_EXTRACTION_PROMPT = (
    "This is a restaurant purchase invoice or delivery receipt. "
    "Extract each line item as JSON with fields: name, quantity, unit, unit_price, total_price. "
    "Also return supplier name and invoice date if visible. Respond with JSON only."
)


class VisionResponse(BaseModel):
    result: str


@router.post("/parse", response_model=VisionResponse)
async def parse_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
) -> VisionResponse:
    """Parse an uploaded image using Claude Vision and return the raw reply."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = parse_image_with_claude(
            image_base64=base64.b64encode(raw).decode("ascii"),
            prompt=prompt or _DEFAULT_EXTRACTION_PROMPT,
            media_type=file.content_type,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return VisionResponse(result=result)
