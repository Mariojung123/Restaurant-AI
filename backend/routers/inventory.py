"""
Inventory endpoints.

Skeleton routes for listing ingredients, recording stock changes, and
retrieving depletion forecasts. Business logic is intentionally minimal
and will be expanded as the MVP matures.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import Ingredient, InventoryLog, get_db
from services.prediction import forecast_all, forecast_ingredient


router = APIRouter()


class IngredientOut(BaseModel):
    """Ingredient representation returned by the API."""

    id: int
    name: str
    unit: str
    current_stock: float
    reorder_threshold: float

    class Config:
        from_attributes = True


class InventoryLogIn(BaseModel):
    """Payload for recording an inventory change."""

    ingredient_id: int
    change_type: str = Field(..., description="purchase | delivery | adjustment")
    quantity: float
    unit_cost: Optional[float] = None
    supplier: Optional[str] = None
    note: Optional[str] = None


class ForecastOut(BaseModel):
    """Depletion forecast shape for a single ingredient."""

    ingredient_id: int
    ingredient_name: str
    current_stock: float
    daily_consumption: float
    days_remaining: Optional[float]
    depletion_date: Optional[str]
    reorder_threshold: float
    needs_reorder: bool


@router.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients(db: Session = Depends(get_db)) -> list[IngredientOut]:
    """Return every tracked ingredient."""
    return db.query(Ingredient).order_by(Ingredient.name).all()


@router.post("/logs", status_code=201)
def create_inventory_log(
    payload: InventoryLogIn,
    db: Session = Depends(get_db),
) -> dict:
    """Record an inventory change and adjust the ingredient's current stock."""
    ingredient = db.query(Ingredient).filter(Ingredient.id == payload.ingredient_id).first()
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    log = InventoryLog(
        ingredient_id=payload.ingredient_id,
        change_type=payload.change_type,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        supplier=payload.supplier,
        note=payload.note,
    )
    ingredient.current_stock += payload.quantity

    db.add(log)
    db.commit()
    db.refresh(log)
    return {"id": log.id, "current_stock": ingredient.current_stock}


@router.get("/forecast", response_model=list[ForecastOut])
def get_forecast(db: Session = Depends(get_db)) -> list[ForecastOut]:
    """Return a depletion forecast for every ingredient."""
    forecasts = forecast_all(db)
    return [
        ForecastOut(
            ingredient_id=f.ingredient_id,
            ingredient_name=f.ingredient_name,
            current_stock=f.current_stock,
            daily_consumption=f.daily_consumption,
            days_remaining=f.days_remaining,
            depletion_date=f.depletion_date.isoformat() if f.depletion_date else None,
            reorder_threshold=f.reorder_threshold,
            needs_reorder=f.needs_reorder,
        )
        for f in forecasts
    ]


@router.get("/forecast/{ingredient_id}", response_model=ForecastOut)
def get_forecast_for_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
) -> ForecastOut:
    """Return a depletion forecast for a single ingredient."""
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    f = forecast_ingredient(db, ingredient)
    return ForecastOut(
        ingredient_id=f.ingredient_id,
        ingredient_name=f.ingredient_name,
        current_stock=f.current_stock,
        daily_consumption=f.daily_consumption,
        days_remaining=f.days_remaining,
        depletion_date=f.depletion_date.isoformat() if f.depletion_date else None,
        reorder_threshold=f.reorder_threshold,
        needs_reorder=f.needs_reorder,
    )
