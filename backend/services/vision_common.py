"""Shared utilities for vision (image-parsing) endpoints."""

import base64
import json
from typing import Type, TypeVar

from fastapi import HTTPException, UploadFile

from services.claude import parse_image_with_claude, strip_fences

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

T = TypeVar("T")


async def read_upload_file(file: UploadFile) -> bytes:
    """Validate content type and return raw bytes. Raises HTTPException on failure."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    return raw_bytes


def encode_image(raw_bytes: bytes) -> str:
    return base64.b64encode(raw_bytes).decode("ascii")


def call_vision_api(raw_bytes: bytes, content_type: str, prompt: str, max_tokens: int = 2048) -> str:
    """Call Claude vision API. Raises HTTPException(500) on RuntimeError."""
    try:
        return parse_image_with_claude(
            image_base64=encode_image(raw_bytes),
            prompt=prompt,
            media_type=content_type,
            max_tokens=max_tokens,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def parse_vision_json(raw: str, model_class: Type[T], doc_type: str = "document") -> T:
    """Parse Claude JSON response into a Pydantic model. Raises ValueError on failure."""
    cleaned = strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned non-JSON: {exc}") from exc
    try:
        return model_class.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Invalid {doc_type} structure: {exc}") from exc
