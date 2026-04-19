"""Chat history persistence helpers."""

from sqlalchemy.orm import Session

from models.database import ChatHistory


def load_history(db: Session, session_id: str, limit: int = 20) -> list[dict]:
    rows = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.session_id == session_id,
            ChatHistory.role.in_(["user", "assistant"]),
        )
        .order_by(ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )
    return [{"role": r.role, "content": r.content} for r in rows]


def append_history(db: Session, session_id: str, messages: list, reply: str) -> None:
    for msg in messages:
        db.add(ChatHistory(session_id=session_id, role=msg.role, content=msg.content))
    db.add(ChatHistory(session_id=session_id, role="assistant", content=reply))
