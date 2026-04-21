import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from services.chat_context import build_context, build_system_prompt
from services.chat_history import append_history, delete_history, load_history
from services.claude import (
    RECIPE_TOOL,
    chat_with_claude,
    extract_text,
    extract_tool_use_block,
    message_content_to_dicts,
)
from services.recipe_svc import register_recipe_from_tool

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    session_id: str
    messages: list[ChatMessage]
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


def _run_recipe_tool(
    db: Session,
    all_messages: list[dict],
    system: str,
    first_response,
) -> str:
    """Execute register_recipe tool call, then get Claude's follow-up text reply."""
    tool_block = extract_tool_use_block(first_response)
    if tool_block is None:
        return extract_text(first_response)

    tool_id, tool_name, tool_input = tool_block

    if tool_name != "register_recipe":
        logger.warning("Unexpected tool call: %s", tool_name)
        return extract_text(first_response)

    try:
        result = register_recipe_from_tool(
            db,
            name=tool_input["name"],
            price=tool_input.get("price", 0.0),
            items=tool_input["items"],
        )
        db.commit()
        tool_result = f"Success: '{result['name']}' registered. Linked {result['ingredients_linked']} ingredient(s), created {result['ingredients_created']} new."
    except ValueError as e:
        tool_result = f"Error: {e}"

    follow_up = all_messages + [
        {"role": "assistant", "content": message_content_to_dicts(first_response.content)},
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": tool_result}],
        },
    ]
    try:
        final = chat_with_claude(follow_up, system, tools=[RECIPE_TOOL])
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return extract_text(final)


def _handle_chat(
    db: Session,
    session_id: str,
    messages: list[ChatMessage],
    user_message: str,
) -> ChatResponse:
    history = load_history(db, session_id)
    context = build_context(db, user_message)
    system = build_system_prompt(context)
    all_messages = history + [m.model_dump() for m in messages]

    try:
        response = chat_with_claude(all_messages, system, tools=[RECIPE_TOOL])
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if response.stop_reason == "tool_use":
        reply = _run_recipe_tool(db, all_messages, system, response)
    else:
        reply = extract_text(response)

    append_history(db, session_id, messages, reply)
    db.commit()
    return ChatResponse(reply=reply, session_id=session_id)


@router.post("/message", response_model=ChatResponse)
def send_message(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    last_user_msg = next(
        (m.content for m in reversed(payload.messages) if m.role == "user"), ""
    )
    return _handle_chat(db, payload.session_id, payload.messages, last_user_msg)


@router.get("/history/{session_id}")
def get_history(session_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return load_history(db, session_id, limit=200)


@router.delete("/history/{session_id}", status_code=204)
def clear_history(session_id: str, db: Session = Depends(get_db)) -> None:
    delete_history(db, session_id)
    db.commit()
