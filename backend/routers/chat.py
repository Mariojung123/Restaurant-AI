"""
Chat endpoints.

Exposes a simple message endpoint that forwards the conversation to Claude.
Real orchestration (tool calls, context injection, memory) will be added later.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.claude import chat_with_claude


router = APIRouter()


class ChatMessage(BaseModel):
    """A single conversation turn."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    """Payload for /api/chat/message."""

    messages: list[ChatMessage]
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    """Response wrapping Claude's plain-text reply."""

    reply: str


@router.post("/message", response_model=ChatResponse)
def send_message(payload: ChatRequest) -> ChatResponse:
    """Forward a chat history to Claude and return the assistant reply."""
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    try:
        reply = chat_with_claude(
            messages=[m.model_dump() for m in payload.messages],
            system_prompt=payload.system_prompt,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(reply=reply)
