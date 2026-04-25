from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.database import Recipe, SalesLog


@dataclass
class ReceiptItem:
    recipe_name: str
    quantity: int
    total_price: Optional[float]


@dataclass
class ReceiptSummary:
    date: str
    item_count: int
    total_revenue: Optional[float]
    items: list[ReceiptItem] = field(default_factory=list)


@dataclass
class ReceiptHistoryResult:
    this_week_total: Optional[float]
    this_month_total: Optional[float]
    receipts: list[ReceiptSummary]


def _week_start(now: datetime) -> datetime:
    return (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_receipt_history(db: Session) -> ReceiptHistoryResult:
    rows = (
        db.query(SalesLog, Recipe)
        .join(Recipe, Recipe.id == SalesLog.recipe_id)
        .order_by(SalesLog.sold_at.desc())
        .all()
    )

    groups: dict[str, list[tuple]] = {}
    for log, recipe in rows:
        date_str = log.sold_at.strftime("%Y-%m-%d")
        groups.setdefault(date_str, []).append((log, recipe))

    now = datetime.now(timezone.utc)
    week_start = _week_start(now)
    month_start = _month_start(now)
    this_week_total = 0.0
    this_month_total = 0.0
    week_has_revenue = False
    month_has_revenue = False

    receipts: list[ReceiptSummary] = []
    for date_str, items in groups.items():
        receipt_items: list[ReceiptItem] = []
        day_total = 0.0
        has_revenue = False
        for log, recipe in items:
            if log.total_price is not None:
                day_total += log.total_price
                has_revenue = True
                occurred = log.sold_at
                if occurred.tzinfo is None:
                    occurred = occurred.replace(tzinfo=timezone.utc)
                if occurred >= month_start:
                    this_month_total += log.total_price
                    month_has_revenue = True
                if occurred >= week_start:
                    this_week_total += log.total_price
                    week_has_revenue = True
            receipt_items.append(
                ReceiptItem(
                    recipe_name=recipe.name,
                    quantity=log.quantity,
                    total_price=log.total_price,
                )
            )
        receipts.append(
            ReceiptSummary(
                date=date_str,
                item_count=len(receipt_items),
                total_revenue=day_total if has_revenue else None,
                items=receipt_items,
            )
        )

    receipts.sort(key=lambda x: x.date, reverse=True)

    return ReceiptHistoryResult(
        this_week_total=this_week_total if week_has_revenue else None,
        this_month_total=this_month_total if month_has_revenue else None,
        receipts=receipts,
    )
