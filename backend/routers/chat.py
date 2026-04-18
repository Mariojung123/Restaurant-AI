from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import ChatHistory, Ingredient, Recipe, RecipeIngredient, SalesLog, get_db
from services.claude import DEFAULT_SYSTEM_PROMPT, chat_with_claude
from services.prediction import forecast_all

router = APIRouter()

INVENTORY_KEYWORDS = {"재고", "stock", "inventory", "ingredient", "떨어", "소진", "남은", "남았", "얼마나", "몇 kg", "몇kg"}
SALES_KEYWORDS = {"판매", "sales", "sell", "sold", "잘 팔", "많이 팔", "revenue", "매출", "팔렸", "팔린", "인기"}
RECIPE_KEYWORDS = {"레시피", "recipe", "menu", "메뉴"}


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


def _load_history(db: Session, session_id: str, limit: int = 20) -> list[dict]:
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )
    return [{"role": r.role, "content": r.content} for r in rows]


def _build_context(db: Session, user_message: str) -> str:
    msg_lower = user_message.lower()
    blocks = []

    ingredients = db.query(Ingredient).all()
    if ingredients:
        forecasts = {f.ingredient_id: f for f in forecast_all(db)}
        lines = ["Ingredient | Unit | Stock | Days Left | Needs Reorder"]
        lines.append("-" * 60)
        for ing in ingredients:
            fc = forecasts.get(ing.id)
            days = f"{fc.days_remaining:.1f}" if fc and fc.daily_consumption > 0 else "N/A"
            reorder = "YES" if fc and fc.needs_reorder else "no"
            lines.append(f"{ing.name} | {ing.unit} | {ing.current_stock} | {days} | {reorder}")
        blocks.append("=== Inventory & Forecast ===\n" + "\n".join(lines))

    if any(kw in msg_lower for kw in SALES_KEYWORDS):
        since = datetime.utcnow() - timedelta(days=7)
        rows = (
            db.query(Recipe.name, func.sum(SalesLog.quantity).label("total_qty"))
            .join(SalesLog, SalesLog.recipe_id == Recipe.id)
            .filter(SalesLog.sold_at >= since)
            .group_by(Recipe.name)
            .order_by(func.sum(SalesLog.quantity).desc())
            .all()
        )
        if rows:
            lines = ["Menu | Qty Sold (last 7 days)"]
            lines.append("-" * 40)
            for name, qty in rows:
                lines.append(f"{name} | {qty}")
            blocks.append("=== Sales (last 7 days) ===\n" + "\n".join(lines))

    if any(kw in msg_lower for kw in RECIPE_KEYWORDS):
        recipes = db.query(Recipe).all()
        if recipes:
            lines = ["Menu | Price | Description"]
            lines.append("-" * 50)
            for r in recipes:
                lines.append(f"{r.name} | ${r.price or 'N/A'} | {r.description or ''}")
            blocks.append("=== Recipes / Menu ===\n" + "\n".join(lines))

    return "\n\n".join(blocks)


def _build_system_prompt(context: str) -> str:
    if not context:
        return DEFAULT_SYSTEM_PROMPT + "\n\nAlways respond in the same language the user writes in."
    return (
        DEFAULT_SYSTEM_PROMPT
        + "\n\n--- Current restaurant data ---\n"
        + context
        + "\n--- End of data ---"
        + "\n\nAlways respond in the same language the user writes in."
    )


@router.post("/message", response_model=ChatResponse)
def send_message(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    history = _load_history(db, payload.session_id)
    last_user_msg = next(
        (m.content for m in reversed(payload.messages) if m.role == "user"), ""
    )
    context = _build_context(db, last_user_msg)
    system = _build_system_prompt(context)

    all_messages = history + [m.model_dump() for m in payload.messages]

    try:
        reply = chat_with_claude(messages=all_messages, system_prompt=system)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    for msg in payload.messages:
        db.add(ChatHistory(session_id=payload.session_id, role=msg.role, content=msg.content))
    db.add(ChatHistory(session_id=payload.session_id, role="assistant", content=reply))
    db.commit()

    return ChatResponse(reply=reply, session_id=payload.session_id)


@router.get("/history/{session_id}")
def get_history(session_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return _load_history(db, session_id, limit=100)
