import json
import logging
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from services.chat_context import build_context, build_system_prompt, matches_any
from services.chat_history import append_history, delete_history, load_history
from services.claude import chat_with_claude, detect_recipe_update, extract_recipe_from_chat
from services.pending_recipe import (
    _has_korean,
    apply_pending_update,
    clear_pending,
    format_confirmation_message,
    get_pending,
    resolve_items,
    save_pending,
)
from services.recipe_svc import save_recipe_core

logger = logging.getLogger(__name__)

router = APIRouter()

RECIPE_REGISTER_KEYWORDS = {
    "레시피 등록", "레시피를 등록", "레시피 추가", "레시피를 추가",
    "레시피 저장", "레시피를 저장",
    "register recipe", "add recipe", "save recipe", "create recipe",
    "new recipe", "a recipe", "add a recipe",
    "등록해줘", "등록해 줘", "추가해줘", "추가해 줘", "저장해줘", "저장해 줘",
}
CONFIRM_KEYWORDS = {"응", "네", "예", "좋아", "ok", "yes", "맞아", "ㅇㅇ", "확인", "등록해", "등록해줘"}
REJECT_KEYWORDS = {"아니", "취소", "no", "cancel", "ㄴㄴ", "싫어", "그만", "하지마"}


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


def _is_recipe_register_intent(msg: str) -> bool:
    return matches_any(msg, RECIPE_REGISTER_KEYWORDS)


def _is_confirmation(msg: str) -> bool:
    stripped = msg.strip().lower()
    return any(stripped == kw or stripped.startswith(kw + " ") for kw in CONFIRM_KEYWORDS)


def _is_rejection(msg: str) -> bool:
    return matches_any(msg.strip(), REJECT_KEYWORDS)


def _handle_pending_confirmation(
    db: Session, session_id: str, messages: list[ChatMessage], pending: dict
) -> Optional[ChatResponse]:
    korean = pending.get("lang") == "ko"
    try:
        resolved = resolve_items(db, pending)
        result = save_recipe_core(
            db,
            name=pending["name"],
            description=pending.get("description"),
            price=pending.get("price", 0.0),
            resolved_items=resolved,
        )
        if korean:
            reply = (
                f"✅ **{result['name']}** 레시피 등록 완료!\n"
                f"재료 {result['ingredients_linked']}개 기존 재고와 연결, "
                f"{result['ingredients_created']}개 새로 생성했어요."
            )
        else:
            reply = (
                f"✅ **{result['name']}** has been added!\n"
                f"{result['ingredients_linked']} ingredient(s) matched to existing stock, "
                f"{result['ingredients_created']} new one(s) created."
            )
    except ValueError as e:
        reply = f"⚠️ {e}"
    clear_pending(db, session_id)
    append_history(db, session_id, messages, reply)
    db.commit()
    return ChatResponse(reply=reply, session_id=session_id)


def _handle_pending_rejection(
    db: Session, session_id: str, messages: list[ChatMessage], pending: dict
) -> ChatResponse:
    korean = pending.get("lang") == "ko"
    reply = (
        f"'{pending['name']}' 레시피 등록을 취소했어요."
        if korean
        else f"Cancelled adding '{pending['name']}'."
    )
    clear_pending(db, session_id)
    append_history(db, session_id, messages, reply)
    db.commit()
    return ChatResponse(reply=reply, session_id=session_id)


def _handle_pending_update(
    db: Session, session_id: str, messages: list[ChatMessage], updated: dict
) -> ChatResponse:
    save_pending(db, session_id, updated)
    reply = format_confirmation_message(updated)
    append_history(db, session_id, messages, reply)
    db.commit()
    return ChatResponse(reply=reply, session_id=session_id)


def _handle_recipe_register(
    db: Session, session_id: str, messages: list[ChatMessage], user_message: str
) -> Optional[ChatResponse]:
    try:
        history = load_history(db, session_id)
        parsed = extract_recipe_from_chat(user_message, history=history)
        parsed["lang"] = "ko" if _has_korean(user_message) else "en"
        save_pending(db, session_id, parsed)
        reply = format_confirmation_message(parsed)
        append_history(db, session_id, messages, reply)
        db.commit()
        return ChatResponse(reply=reply, session_id=session_id)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("Recipe parse failed, falling through to chat: %s", e)
        return None


def _handle_normal_chat(
    db: Session, session_id: str, messages: list[ChatMessage], user_message: str
) -> ChatResponse:
    history = load_history(db, session_id)
    context = build_context(db, user_message)
    system = build_system_prompt(context)
    all_messages = history + [m.model_dump() for m in messages]

    try:
        reply = chat_with_claude(messages=all_messages, system_prompt=system)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

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

    pending = get_pending(db, payload.session_id)
    if pending:
        if _is_confirmation(last_user_msg):
            return _handle_pending_confirmation(db, payload.session_id, payload.messages, pending)
        if _is_rejection(last_user_msg):
            return _handle_pending_rejection(db, payload.session_id, payload.messages, pending)
        try:
            updates = detect_recipe_update(pending, last_user_msg)
            if updates:
                updated = apply_pending_update(pending, updates)
                return _handle_pending_update(db, payload.session_id, payload.messages, updated)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Recipe update parse failed, falling through to chat: %s", e)

    if not pending and _is_recipe_register_intent(last_user_msg):
        result = _handle_recipe_register(db, payload.session_id, payload.messages, last_user_msg)
        if result:
            return result

    return _handle_normal_chat(db, payload.session_id, payload.messages, last_user_msg)


@router.get("/history/{session_id}")
def get_history(session_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return load_history(db, session_id, limit=200)


@router.delete("/history/{session_id}", status_code=204)
def clear_history(session_id: str, db: Session = Depends(get_db)) -> None:
    delete_history(db, session_id)
    db.commit()
