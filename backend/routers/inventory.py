"""
Inventory endpoints.

Skeleton routes for listing ingredients, recording stock changes, and
retrieving depletion forecasts. Business logic is intentionally minimal
and will be expanded as the MVP matures.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from models.database import Ingredient, get_db
from services.ingredient import delete_ingredient, update_ingredient
from services.inventory_svc import record_inventory_change
from services.prediction import (
    DEFAULT_LOOKBACK_DAYS,
    daily_usage_history,
    forecast_all,
    forecast_ingredient,
)


router = APIRouter()


class IngredientOut(BaseModel):
    """Ingredient representation returned by the API."""

    id: int
    name: str
    unit: str
    current_stock: float
    reorder_threshold: float

    model_config = ConfigDict(from_attributes=True)


class InventoryLogIn(BaseModel):
    """Payload for recording an inventory change."""

    ingredient_id: int
    change_type: str = Field(..., description="purchase | delivery | adjustment")
    quantity: float
    unit_cost: Optional[float] = None
    supplier: Optional[str] = None
    note: Optional[str] = None


class IngredientUpdate(BaseModel):
    """Payload for updating an ingredient's stock and reorder threshold."""

    current_stock: Optional[float] = None
    reorder_threshold: Optional[float] = None


class DailyUsageOut(BaseModel):
    """Per-day ingredient consumption returned by the history endpoint."""

    date: str
    amount: float


class ForecastOut(BaseModel):
    """Depletion forecast shape for a single ingredient."""

    ingredient_id: int
    ingredient_name: str
    unit: str
    current_stock: float
    daily_consumption: float
    days_remaining: Optional[float]
    depletion_date: Optional[str]
    reorder_threshold: float
    needs_reorder: bool
    last_purchase_date: Optional[str]


@router.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients(db: Session = Depends(get_db)) -> list[IngredientOut]:
    """Return every tracked ingredient."""
    return db.query(Ingredient).filter(Ingredient.is_deleted == False).order_by(Ingredient.name).all()  # noqa: E712


@router.post("/logs", status_code=201)
def create_inventory_log(
    payload: InventoryLogIn,
    db: Session = Depends(get_db),
) -> dict:
    """Record an inventory change and adjust the ingredient's current stock."""
    try:
        log, current_stock = record_inventory_change(
            db,
            ingredient_id=payload.ingredient_id,
            change_type=payload.change_type,
            quantity=payload.quantity,
            unit_cost=payload.unit_cost,
            supplier=payload.supplier,
            note=payload.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    db.commit()
    db.refresh(log)
    return {"id": log.id, "current_stock": current_stock}


@router.get("/forecast", response_model=list[ForecastOut])
def get_forecast(db: Session = Depends(get_db)) -> list[ForecastOut]:
    """Return a depletion forecast for every ingredient."""
    forecasts = forecast_all(db)
    return [
        ForecastOut(
            ingredient_id=f.ingredient_id,
            ingredient_name=f.ingredient_name,
            unit=f.unit,
            current_stock=f.current_stock,
            daily_consumption=f.daily_consumption,
            days_remaining=f.days_remaining,
            depletion_date=f.depletion_date.isoformat() if f.depletion_date else None,
            reorder_threshold=f.reorder_threshold,
            needs_reorder=f.needs_reorder,
            last_purchase_date=f.last_purchase_date.isoformat() if f.last_purchase_date else None,
        )
        for f in forecasts
    ]


@router.get("/history/{ingredient_id}", response_model=list[DailyUsageOut])
def get_usage_history(
    ingredient_id: int,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    db: Session = Depends(get_db),
) -> list[DailyUsageOut]:
    """Return per-day consumption of a single ingredient over the lookback window."""
    ingredient = db.query(Ingredient).filter(Ingredient.is_deleted == False, Ingredient.id == ingredient_id).first()  # noqa: E712
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    history = daily_usage_history(db, ingredient_id, lookback_days)
    return [DailyUsageOut(date=h.date, amount=h.amount) for h in history]


@router.get("/forecast/{ingredient_id}", response_model=ForecastOut)
def get_forecast_for_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
) -> ForecastOut:
    """Return a depletion forecast for a single ingredient."""
    ingredient = db.query(Ingredient).filter(Ingredient.is_deleted == False, Ingredient.id == ingredient_id).first()  # noqa: E712
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    f = forecast_ingredient(db, ingredient)
    return ForecastOut(
        ingredient_id=f.ingredient_id,
        ingredient_name=f.ingredient_name,
        unit=f.unit,
        current_stock=f.current_stock,
        daily_consumption=f.daily_consumption,
        days_remaining=f.days_remaining,
        depletion_date=f.depletion_date.isoformat() if f.depletion_date else None,
        reorder_threshold=f.reorder_threshold,
        needs_reorder=f.needs_reorder,
        last_purchase_date=f.last_purchase_date.isoformat() if f.last_purchase_date else None,
    )


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientOut)
def patch_ingredient(
    ingredient_id: int,
    payload: IngredientUpdate,
    db: Session = Depends(get_db),
) -> IngredientOut:
    """Update current_stock and/or reorder_threshold for an ingredient."""
    existing = db.query(Ingredient).filter(Ingredient.is_deleted == False, Ingredient.id == ingredient_id).first()  # noqa: E712
    if existing is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    new_stock = payload.current_stock if payload.current_stock is not None else existing.current_stock
    new_threshold = payload.reorder_threshold if payload.reorder_threshold is not None else existing.reorder_threshold

    try:
        updated = update_ingredient(db, ingredient_id, new_stock, new_threshold)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    db.commit()
    db.refresh(updated)
    return updated


@router.delete("/ingredients/{ingredient_id}", status_code=204)
def remove_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Permanently remove an ingredient from the database."""
    try:
        delete_ingredient(db, ingredient_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    db.commit()
