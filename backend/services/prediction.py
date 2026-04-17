"""
Inventory depletion prediction service.

Given historical sales and inventory logs, estimate when each ingredient will
run out. Business logic is a simple linear projection today; more sophisticated
pattern detection (weekday seasonality, promotions) will be layered on later.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from models.database import Ingredient, InventoryLog, RecipeIngredient, SalesLog


# Default lookback window for computing daily consumption rate
DEFAULT_LOOKBACK_DAYS = 14


@dataclass
class DepletionForecast:
    """Projected depletion data for a single ingredient."""

    ingredient_id: int
    ingredient_name: str
    current_stock: float
    daily_consumption: float
    days_remaining: Optional[float]
    depletion_date: Optional[datetime]
    reorder_threshold: float
    needs_reorder: bool


def _daily_consumption_for_ingredient(
    db: Session,
    ingredient_id: int,
    lookback_days: int,
) -> float:
    """Estimate average daily consumption of an ingredient over a lookback window."""
    since = datetime.utcnow() - timedelta(days=lookback_days)

    # Join sales_logs -> recipe_ingredients to translate sold dishes into ingredient units
    rows = (
        db.query(SalesLog.quantity, RecipeIngredient.quantity)
        .join(RecipeIngredient, RecipeIngredient.recipe_id == SalesLog.recipe_id)
        .filter(
            RecipeIngredient.ingredient_id == ingredient_id,
            SalesLog.sold_at >= since,
        )
        .all()
    )

    total_used = sum(sold_qty * per_serving for sold_qty, per_serving in rows)
    if lookback_days <= 0:
        return 0.0
    return total_used / float(lookback_days)


def forecast_ingredient(
    db: Session,
    ingredient: Ingredient,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> DepletionForecast:
    """Produce a DepletionForecast for a single ingredient."""
    daily = _daily_consumption_for_ingredient(db, ingredient.id, lookback_days)

    if daily > 0:
        days_remaining = ingredient.current_stock / daily
        depletion_date = datetime.utcnow() + timedelta(days=days_remaining)
    else:
        days_remaining = None
        depletion_date = None

    needs_reorder = ingredient.current_stock <= ingredient.reorder_threshold

    return DepletionForecast(
        ingredient_id=ingredient.id,
        ingredient_name=ingredient.name,
        current_stock=ingredient.current_stock,
        daily_consumption=daily,
        days_remaining=days_remaining,
        depletion_date=depletion_date,
        reorder_threshold=ingredient.reorder_threshold,
        needs_reorder=needs_reorder,
    )


def forecast_all(
    db: Session,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[DepletionForecast]:
    """Produce depletion forecasts for every ingredient in the catalog."""
    ingredients: Iterable[Ingredient] = db.query(Ingredient).all()
    return [forecast_ingredient(db, ing, lookback_days) for ing in ingredients]


def last_purchase(db: Session, ingredient_id: int) -> Optional[InventoryLog]:
    """Return the most recent purchase log for an ingredient, if any."""
    return (
        db.query(InventoryLog)
        .filter(
            InventoryLog.ingredient_id == ingredient_id,
            InventoryLog.change_type == "purchase",
        )
        .order_by(InventoryLog.occurred_at.desc())
        .first()
    )
