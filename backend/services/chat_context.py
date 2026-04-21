"""Context building for the restaurant chat assistant."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import Ingredient, Recipe, SalesLog
from services.claude import DEFAULT_SYSTEM_PROMPT
from services.prediction import forecast_all

INVENTORY_KEYWORDS = {"재고", "stock", "inventory", "ingredient", "떨어", "소진", "남은", "남았", "얼마나", "몇 kg", "몇kg"}
SALES_KEYWORDS = {"판매", "sales", "sell", "sold", "잘 팔", "많이 팔", "revenue", "매출", "팔렸", "팔린", "인기"}
RECIPE_KEYWORDS = {"레시피", "recipe", "menu", "메뉴"}


def matches_any(msg: str, keywords: set[str]) -> bool:
    msg_lower = msg.lower()
    return any(kw in msg_lower for kw in keywords)


def build_context(db: Session, user_message: str) -> str:
    blocks = []

    ingredients = db.query(Ingredient).all()
    if ingredients:
        forecasts = {f.ingredient_id: f for f in forecast_all(db)}
        lines = ["Ingredient | Unit | Stock | Days Left | Needs Reorder", "-" * 60]
        for ing in ingredients:
            fc = forecasts.get(ing.id)
            days = f"{fc.days_remaining:.1f}" if fc and fc.daily_consumption > 0 else "N/A"
            reorder = "YES" if fc and fc.needs_reorder else "no"
            lines.append(f"{ing.name} | {ing.unit} | {ing.current_stock} | {days} | {reorder}")
        blocks.append("=== Inventory & Forecast ===\n" + "\n".join(lines))

    if matches_any(user_message, SALES_KEYWORDS):
        since = datetime.now(timezone.utc) - timedelta(days=7)
        rows = (
            db.query(Recipe.name, func.sum(SalesLog.quantity).label("total_qty"))
            .join(SalesLog, SalesLog.recipe_id == Recipe.id)
            .filter(SalesLog.sold_at >= since)
            .group_by(Recipe.name)
            .order_by(func.sum(SalesLog.quantity).desc())
            .all()
        )
        if rows:
            lines = ["Menu | Qty Sold (last 7 days)", "-" * 40]
            for name, qty in rows:
                lines.append(f"{name} | {qty}")
            blocks.append("=== Sales (last 7 days) ===\n" + "\n".join(lines))

    if matches_any(user_message, RECIPE_KEYWORDS):
        recipes = db.query(Recipe).all()
        if recipes:
            lines = ["Menu | Price | Description", "-" * 50]
            for r in recipes:
                lines.append(f"{r.name} | ${r.price or 'N/A'} | {r.description or ''}")
            blocks.append("=== Recipes / Menu ===\n" + "\n".join(lines))

    return "\n\n".join(blocks)


def build_system_prompt(context: str) -> str:
    base = DEFAULT_SYSTEM_PROMPT + "\n\nAlways respond in the same language the user writes in."
    if not context:
        return base
    return (
        DEFAULT_SYSTEM_PROMPT
        + "\n\n--- Current restaurant data ---\n"
        + context
        + "\n--- End of data ---"
        + "\n\nAlways respond in the same language the user writes in."
    )
