"""Pending recipe flow — temporary storage and resolution before DB commit."""

import json
from typing import Optional

from sqlalchemy.orm import Session

from models.database import ChatHistory
from services.ingredient import FUZZY_MATCH_THRESHOLD, fuzzy_match_ingredient


def get_pending(db: Session, session_id: str) -> Optional[dict]:
    row = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.session_id == session_id,
            ChatHistory.role == "pending_recipe",
        )
        .order_by(ChatHistory.created_at.desc())
        .first()
    )
    return json.loads(row.content) if row else None


def save_pending(db: Session, session_id: str, data: dict) -> None:
    clear_pending(db, session_id)
    db.add(
        ChatHistory(
            session_id=session_id,
            role="pending_recipe",
            content=json.dumps(data, ensure_ascii=False),
        )
    )


def clear_pending(db: Session, session_id: str) -> None:
    db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id,
        ChatHistory.role == "pending_recipe",
    ).delete()


def resolve_items(db: Session, pending: dict) -> list[dict]:
    resolved = []
    for item in pending["items"]:
        match, score = fuzzy_match_ingredient(db, item["name"])
        ingredient = match if (match and score >= FUZZY_MATCH_THRESHOLD) else None
        resolved.append({
            "ingredient": ingredient,
            "name": item["name"],
            "quantity": item.get("quantity"),
            "unit": item.get("unit", "unit"),
            "quantity_display": item.get("quantity_display"),
        })
    return resolved


def format_confirmation_message(parsed: dict) -> str:
    lines = [f"**{parsed['name']}** 레시피를 등록할게요! 아래 재료를 확인해주세요:\n"]
    for item in parsed["items"]:
        line = f"- {item['name']}: {item['quantity_display']} → {item['quantity']}{item['unit']}"
        if item.get("reasoning"):
            line += f"  ({item['reasoning']})"
        lines.append(line)
    lines.append("\n등록할까요? (네 / 아니오)")
    return "\n".join(lines)
