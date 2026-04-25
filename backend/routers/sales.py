"""Sales history endpoint."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db
from services import sales_svc
from services.constants import SALES_DEFAULT_PERIOD_DAYS, SALES_MAX_PERIOD_DAYS

router = APIRouter()


class DailySummaryOut(BaseModel):
    date: str
    revenue: float
    items_sold: int
    items: list["MenuSummaryOut"]


class MenuSummaryOut(BaseModel):
    recipe_id: int
    recipe_name: str
    quantity: int
    revenue: float


class SalesSummaryOut(BaseModel):
    period_days: int
    total_revenue: float
    total_items_sold: int
    daily_summaries: list[DailySummaryOut]
    menu_summaries: list[MenuSummaryOut]


@router.get("", response_model=SalesSummaryOut)
def get_sales(
    period_days: int = Query(default=SALES_DEFAULT_PERIOD_DAYS, ge=1, le=SALES_MAX_PERIOD_DAYS),
    db: Session = Depends(get_db),
) -> SalesSummaryOut:
    summary = sales_svc.get_sales_summary(db, period_days)
    return SalesSummaryOut(
        period_days=summary.period_days,
        total_revenue=summary.total_revenue,
        total_items_sold=summary.total_items_sold,
        daily_summaries=[
            DailySummaryOut(
                date=d.date,
                revenue=d.revenue,
                items_sold=d.items_sold,
                items=[
                    MenuSummaryOut(recipe_id=m.recipe_id, recipe_name=m.recipe_name, quantity=m.quantity, revenue=m.revenue)
                    for m in d.items
                ],
            )
            for d in summary.daily_summaries
        ],
        menu_summaries=[
            MenuSummaryOut(
                recipe_id=m.recipe_id,
                recipe_name=m.recipe_name,
                quantity=m.quantity,
                revenue=m.revenue,
            )
            for m in summary.menu_summaries
        ],
    )
