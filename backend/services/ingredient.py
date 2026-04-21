from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import Ingredient
from services.constants import DEFAULT_UNIT
from services.fuzzy_match import FUZZY_MATCH_THRESHOLD, fuzzy_match

__all__ = [
    "FUZZY_MATCH_THRESHOLD",
    "fuzzy_match_ingredient",
    "find_ingredient_by_name",
    "create_ingredient",
    "update_ingredient",
    "delete_ingredient",
]


def find_ingredient_by_name(db: Session, name: str):
    return (
        db.query(Ingredient)
        .filter(func.lower(Ingredient.name) == name.lower().strip())
        .first()
    )


def fuzzy_match_ingredient(db: Session, name: str) -> tuple:
    return fuzzy_match(db.query(Ingredient).all(), name)


def create_ingredient(db: Session, name: str, unit: str) -> Ingredient:
    ingredient = Ingredient(name=name.strip(), unit=unit or DEFAULT_UNIT, current_stock=0.0)
    db.add(ingredient)
    db.flush()
    return ingredient


def update_ingredient(
    db: Session,
    ingredient_id: int,
    current_stock: float,
    reorder_threshold: float,
) -> Ingredient:
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient is None:
        raise ValueError(f"Ingredient {ingredient_id} not found")
    ingredient.current_stock = current_stock
    ingredient.reorder_threshold = reorder_threshold
    db.flush()
    return ingredient


def delete_ingredient(db: Session, ingredient_id: int) -> None:
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient is None:
        raise ValueError(f"Ingredient {ingredient_id} not found")
    db.delete(ingredient)
    db.flush()
