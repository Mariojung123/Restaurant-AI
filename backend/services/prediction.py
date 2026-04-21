"""
Inventory depletion prediction service.

Given historical sales and inventory logs, estimate when each ingredient will
run out. Business logic is a simple linear projection today; more sophisticated
pattern detection (weekday seasonality, promotions) will be layered on later.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from models.database import Ingredient, InventoryLog, RecipeIngredient, SalesLog
from services.constants import CHANGE_TYPE_PURCHASE
from services.unit_convert import convert_quantity


@dataclass
class DailyUsage:
    """Ingredient consumption amount for a single calendar day."""

    date: str   # YYYY-MM-DD
    amount: float


# Default lookback window for computing daily consumption rate
DEFAULT_LOOKBACK_DAYS = 7


@dataclass
class DepletionForecast:
    """Projected depletion data for a single ingredient."""

    ingredient_id: int
    ingredient_name: str
    unit: str
    current_stock: float
    daily_consumption: float
    days_remaining: Optional[float]
    depletion_date: Optional[datetime]
    reorder_threshold: float
    needs_reorder: bool
    last_purchase_date: Optional[datetime]


def _daily_consumption_for_ingredient(
    db: Session,
    ingredient: Ingredient,
    lookback_days: int,
) -> float:
    """Estimate average daily consumption of an ingredient over a lookback window."""
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    rows = (
        db.query(SalesLog.quantity, RecipeIngredient.quantity, RecipeIngredient.unit)
        .join(RecipeIngredient, RecipeIngredient.recipe_id == SalesLog.recipe_id)
        .filter(
            RecipeIngredient.ingredient_id == ingredient.id,
            SalesLog.sold_at >= since,
        )
        .all()
    )

    total_used = sum(
        sold_qty * convert_quantity(per_serving, ri_unit, ingredient.unit)
        for sold_qty, per_serving, ri_unit in rows
        if per_serving is not None
    )
    if lookback_days <= 0:
        return 0.0
    return total_used / float(lookback_days)


def forecast_ingredient(
    db: Session,
    ingredient: Ingredient,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> DepletionForecast:
    """Produce a DepletionForecast for a single ingredient."""
    daily = _daily_consumption_for_ingredient(db, ingredient, lookback_days)

    if daily > 0:
        days_remaining = ingredient.current_stock / daily
        depletion_date = datetime.now(timezone.utc) + timedelta(days=days_remaining)
    else:
        days_remaining = None
        depletion_date = None

    needs_reorder = ingredient.current_stock <= ingredient.reorder_threshold
    purchase_log = last_purchase(db, ingredient.id)
    last_purchase_date = purchase_log.occurred_at if purchase_log else None

    return DepletionForecast(
        ingredient_id=ingredient.id,
        ingredient_name=ingredient.name,
        unit=ingredient.unit,
        current_stock=ingredient.current_stock,
        daily_consumption=daily,
        days_remaining=days_remaining,
        depletion_date=depletion_date,
        reorder_threshold=ingredient.reorder_threshold,
        needs_reorder=needs_reorder,
        last_purchase_date=last_purchase_date,
    )


def forecast_all(
    db: Session,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[DepletionForecast]:
    """Produce depletion forecasts for every ingredient in the catalog."""
    ingredients: Iterable[Ingredient] = db.query(Ingredient).filter(Ingredient.is_deleted == False).all()  # noqa: E712
    return [forecast_ingredient(db, ing, lookback_days) for ing in ingredients]


def daily_usage_history(
    db: Session,
    ingredient_id: int,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[DailyUsage]:
    """Return per-day consumption of an ingredient over the lookback window."""
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient is None:
        return []

    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    rows = (
        db.query(SalesLog.sold_at, SalesLog.quantity, RecipeIngredient.quantity, RecipeIngredient.unit)
        .join(RecipeIngredient, RecipeIngredient.recipe_id == SalesLog.recipe_id)
        .filter(
            RecipeIngredient.ingredient_id == ingredient_id,
            SalesLog.sold_at >= since,
        )
        .all()
    )

    daily: dict[str, float] = {}
    for sold_at, sold_qty, per_serving, ri_unit in rows:
        if per_serving is None:
            continue
        date_key = sold_at.strftime("%Y-%m-%d")
        converted = convert_quantity(per_serving, ri_unit, ingredient.unit)
        daily[date_key] = daily.get(date_key, 0.0) + sold_qty * converted

    result: list[DailyUsage] = []
    for i in range(lookback_days):
        day = datetime.now(timezone.utc) - timedelta(days=lookback_days - 1 - i)
        date_str = day.strftime("%Y-%m-%d")
        result.append(DailyUsage(date=date_str, amount=daily.get(date_str, 0.0)))
    return result


def last_purchase(db: Session, ingredient_id: int) -> Optional[InventoryLog]:
    """Return the most recent purchase log for an ingredient, if any."""
    return (
        db.query(InventoryLog)
        .filter(
            InventoryLog.ingredient_id == ingredient_id,
            InventoryLog.change_type == CHANGE_TYPE_PURCHASE,
        )
        .order_by(InventoryLog.occurred_at.desc())
        .first()
    )
