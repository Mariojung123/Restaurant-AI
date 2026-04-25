from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.database import Ingredient, InventoryLog
from services.constants import AUTO_INVOICE_NOTE, CHANGE_TYPE_DELIVERY, INVOICE_UNKNOWN_SUPPLIER


@dataclass
class InvoiceItem:
    ingredient_name: str
    quantity: float
    unit: str
    unit_cost: Optional[float]
    line_total: Optional[float]


@dataclass
class InvoiceSummary:
    supplier: str
    date: str
    item_count: int
    total_cost: Optional[float]
    items: list[InvoiceItem] = field(default_factory=list)


@dataclass
class InvoiceHistoryResult:
    this_week_total: Optional[float]
    this_month_total: Optional[float]
    invoices: list[InvoiceSummary]


def _week_start(now: datetime) -> datetime:
    return (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_invoice_history(db: Session) -> InvoiceHistoryResult:
    rows = (
        db.query(InventoryLog, Ingredient)
        .join(Ingredient, Ingredient.id == InventoryLog.ingredient_id)
        .filter(
            InventoryLog.change_type == CHANGE_TYPE_DELIVERY,
            InventoryLog.note == AUTO_INVOICE_NOTE,
        )
        .order_by(InventoryLog.occurred_at.desc())
        .all()
    )

    groups: dict[tuple[str, str], list[tuple]] = {}
    for log, ingredient in rows:
        date_str = log.occurred_at.strftime("%Y-%m-%d")
        supplier = log.supplier or INVOICE_UNKNOWN_SUPPLIER
        key = (supplier, date_str)
        groups.setdefault(key, []).append((log, ingredient))

    now = datetime.now(timezone.utc)
    week_start = _week_start(now)
    month_start = _month_start(now)
    this_week_total = 0.0
    this_month_total = 0.0
    week_has_cost = False
    month_has_cost = False

    invoices: list[InvoiceSummary] = []
    for (supplier, date_str), items in groups.items():
        line_items: list[InvoiceItem] = []
        invoice_total = 0.0
        has_cost = False
        for log, ingredient in items:
            line_total = None
            if log.unit_cost is not None:
                line_total = log.quantity * log.unit_cost
                invoice_total += line_total
                has_cost = True
                occurred = log.occurred_at
                if occurred.tzinfo is None:
                    occurred = occurred.replace(tzinfo=timezone.utc)
                if occurred >= month_start:
                    this_month_total += line_total
                    month_has_cost = True
                if occurred >= week_start:
                    this_week_total += line_total
                    week_has_cost = True
            line_items.append(
                InvoiceItem(
                    ingredient_name=ingredient.name,
                    quantity=log.quantity,
                    unit=ingredient.unit,
                    unit_cost=log.unit_cost,
                    line_total=line_total,
                )
            )
        invoices.append(
            InvoiceSummary(
                supplier=supplier,
                date=date_str,
                item_count=len(line_items),
                total_cost=invoice_total if has_cost else None,
                items=line_items,
            )
        )

    invoices.sort(key=lambda x: x.date, reverse=True)

    return InvoiceHistoryResult(
        this_week_total=this_week_total if week_has_cost else None,
        this_month_total=this_month_total if month_has_cost else None,
        invoices=invoices,
    )
