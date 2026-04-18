import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import ChatHistory, Ingredient, Recipe, RecipeIngredient, SalesLog, get_db
from services.claude import DEFAULT_SYSTEM_PROMPT, chat_with_claude, extract_recipe_from_chat
from services.invoice import _create_ingredient, fuzzy_match_ingredient
from services.prediction import forecast_all

router = APIRouter()

INVENTORY_KEYWORDS = {"재고", "stock", "inventory", "ingredient", "떨어", "소진", "남은", "남았", "얼마나", "몇 kg", "몇kg"}
SALES_KEYWORDS = {"판매", "sales", "sell", "sold", "잘 팔", "많이 팔", "revenue", "매출", "팔렸", "팔린", "인기"}
RECIPE_KEYWORDS = {"레시피", "recipe", "menu", "메뉴"}

RECIPE_REGISTER_KEYWORDS = {
    "레시피 등록", "레시피를 등록", "레시피 추가", "레시피를 추가",
    "register recipe", "add recipe", "등록해줘", "등록해 줘", "추가해줘", "추가해 줘",
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


def _load_history(db: Session, session_id: str, limit: int = 20) -> list[dict]:
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


def _is_recipe_register_intent(msg: str) -> bool:
    msg_lower = msg.lower()
    return any(kw in msg_lower for kw in RECIPE_REGISTER_KEYWORDS)


def _is_confirmation(msg: str) -> bool:
    stripped = msg.strip().lower()
    return any(stripped == kw or stripped.startswith(kw + " ") for kw in CONFIRM_KEYWORDS)


def _is_rejection(msg: str) -> bool:
    stripped = msg.strip().lower()
    return any(kw in stripped for kw in REJECT_KEYWORDS)


def _get_pending_recipe(db: Session, session_id: str) -> Optional[dict]:
    row = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.session_id == session_id,
            ChatHistory.role == "pending_recipe",
        )
        .order_by(ChatHistory.created_at.desc())
        .first()
    )
    if row:
        return json.loads(row.content)
    return None


def _save_pending_recipe(db: Session, session_id: str, data: dict) -> None:
    _clear_pending_recipe(db, session_id)
    db.add(
        ChatHistory(
            session_id=session_id,
            role="pending_recipe",
            content=json.dumps(data, ensure_ascii=False),
        )
    )


def _clear_pending_recipe(db: Session, session_id: str) -> None:
    db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id,
        ChatHistory.role == "pending_recipe",
    ).delete()


def _format_confirmation_message(parsed: dict) -> str:
    lines = [f"**{parsed['name']}** 레시피를 등록할게요! 아래 재료를 확인해주세요:\n"]
    for item in parsed["items"]:
        line = f"- {item['name']}: {item['quantity_display']} → {item['quantity']}{item['unit']}"
        if item.get("reasoning"):
            line += f"  ({item['reasoning']})"
        lines.append(line)
    lines.append("\n등록할까요? (네 / 아니오)")
    return "\n".join(lines)


def _save_confirmed_recipe(db: Session, pending: dict) -> dict:
    existing = (
        db.query(Recipe)
        .filter(func.lower(Recipe.name) == pending["name"].lower().strip())
        .first()
    )
    if existing:
        raise ValueError(f"'{pending['name']}' 레시피가 이미 존재합니다.")

    recipe = Recipe(
        name=pending["name"],
        description=pending.get("description"),
        price=pending.get("price", 0.0),
    )
    db.add(recipe)
    db.flush()

    linked = 0
    created = 0
    for item in pending["items"]:
        match, score = fuzzy_match_ingredient(db, item["name"])
        if match and score >= 0.7:
            ingredient = match
            linked += 1
        else:
            ingredient = _create_ingredient(db, item["name"], item.get("unit", "unit"))
            created += 1

        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=item.get("quantity"),
                unit=item.get("unit", "unit"),
                quantity_display=item.get("quantity_display"),
            )
        )

    return {"id": recipe.id, "name": recipe.name, "ingredients_linked": linked, "ingredients_created": created}


def _append_history(db: Session, session_id: str, messages: list[ChatMessage], reply: str) -> None:
    for msg in messages:
        db.add(ChatHistory(session_id=session_id, role=msg.role, content=msg.content))
    db.add(ChatHistory(session_id=session_id, role="assistant", content=reply))


@router.post("/message", response_model=ChatResponse)
def send_message(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    last_user_msg = next(
        (m.content for m in reversed(payload.messages) if m.role == "user"), ""
    )

    # ── pending recipe flow ───────────────────────────────────────────────────
    pending = _get_pending_recipe(db, payload.session_id)

    if pending:
        if _is_confirmation(last_user_msg):
            try:
                result = _save_confirmed_recipe(db, pending)
                reply = (
                    f"✅ **{result['name']}** 레시피 등록 완료!\n"
                    f"재료 {result['ingredients_linked']}개 기존 재고와 연결, "
                    f"{result['ingredients_created']}개 새로 생성했어요."
                )
            except ValueError as e:
                reply = f"⚠️ {e}"
            _clear_pending_recipe(db, payload.session_id)
            _append_history(db, payload.session_id, payload.messages, reply)
            db.commit()
            return ChatResponse(reply=reply, session_id=payload.session_id)

        if _is_rejection(last_user_msg):
            _clear_pending_recipe(db, payload.session_id)
            reply = f"'{pending['name']}' 레시피 등록을 취소했어요."
            _append_history(db, payload.session_id, payload.messages, reply)
            db.commit()
            return ChatResponse(reply=reply, session_id=payload.session_id)

    # ── recipe registration intent ────────────────────────────────────────────
    if _is_recipe_register_intent(last_user_msg):
        try:
            parsed = extract_recipe_from_chat(last_user_msg)
            _save_pending_recipe(db, payload.session_id, parsed)
            reply = _format_confirmation_message(parsed)
            _append_history(db, payload.session_id, payload.messages, reply)
            db.commit()
            return ChatResponse(reply=reply, session_id=payload.session_id)
        except Exception:
            pass  # fall through to normal Claude chat

    # ── normal Claude chat ────────────────────────────────────────────────────
    history = _load_history(db, payload.session_id)
    context = _build_context(db, last_user_msg)
    system = _build_system_prompt(context)
    all_messages = history + [m.model_dump() for m in payload.messages]

    try:
        reply = chat_with_claude(messages=all_messages, system_prompt=system)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _append_history(db, payload.session_id, payload.messages, reply)
    db.commit()
    return ChatResponse(reply=reply, session_id=payload.session_id)


@router.get("/history/{session_id}")
def get_history(session_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return _load_history(db, session_id, limit=100)
