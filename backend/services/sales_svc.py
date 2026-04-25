"""Sales history aggregation service."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models.database import Recipe, SalesLog
from services.constants import SALES_DEFAULT_PERIOD_DAYS


@dataclass
class DailySummary:
    date: str
    revenue: float
    items_sold: int
    items: list["MenuSummary"]


@dataclass
class MenuSummary:
    recipe_id: int
    recipe_name: str
    quantity: int
    revenue: float


@dataclass
class SalesSummary:
    period_days: int
    total_revenue: float
    total_items_sold: int
    daily_summaries: list[DailySummary]
    menu_summaries: list[MenuSummary]


def get_sales_summary(db: Session, period_days: int = SALES_DEFAULT_PERIOD_DAYS) -> SalesSummary:
    since = datetime.now(timezone.utc) - timedelta(days=period_days)

    rows = (
        db.query(SalesLog, Recipe.name)
        .join(Recipe, Recipe.id == SalesLog.recipe_id)
        .filter(SalesLog.sold_at >= since)
        .all()
    )

    daily: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "items_sold": 0})
    daily_menu: dict[str, dict[int, dict]] = defaultdict(dict)
    menu: dict[int, dict] = {}
    total_revenue = 0.0
    total_items_sold = 0

    for log, recipe_name in rows:
        revenue = log.total_price or 0.0
        qty = log.quantity
        date_key = log.sold_at.strftime("%Y-%m-%d")

        daily[date_key]["revenue"] += revenue
        daily[date_key]["items_sold"] += qty

        if log.recipe_id not in daily_menu[date_key]:
            daily_menu[date_key][log.recipe_id] = {"recipe_name": recipe_name, "quantity": 0, "revenue": 0.0}
        daily_menu[date_key][log.recipe_id]["quantity"] += qty
        daily_menu[date_key][log.recipe_id]["revenue"] += revenue

        if log.recipe_id not in menu:
            menu[log.recipe_id] = {"recipe_name": recipe_name, "quantity": 0, "revenue": 0.0}
        menu[log.recipe_id]["quantity"] += qty
        menu[log.recipe_id]["revenue"] += revenue

        total_revenue += revenue
        total_items_sold += qty

    daily_summaries = [
        DailySummary(
            date=date,
            revenue=v["revenue"],
            items_sold=v["items_sold"],
            items=[
                MenuSummary(recipe_id=rid, recipe_name=m["recipe_name"], quantity=m["quantity"], revenue=m["revenue"])
                for rid, m in sorted(daily_menu[date].items(), key=lambda x: x[1]["quantity"], reverse=True)
            ],
        )
        for date, v in sorted(daily.items(), reverse=True)
    ]
    menu_summaries = [
        MenuSummary(
            recipe_id=rid,
            recipe_name=v["recipe_name"],
            quantity=v["quantity"],
            revenue=v["revenue"],
        )
        for rid, v in sorted(menu.items(), key=lambda x: x[1]["quantity"], reverse=True)
    ]

    return SalesSummary(
        period_days=period_days,
        total_revenue=total_revenue,
        total_items_sold=total_items_sold,
        daily_summaries=daily_summaries,
        menu_summaries=menu_summaries,
    )
