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

_ACTIVE = Ingredient.is_deleted == False  # noqa: E712


def find_ingredient_by_name(db: Session, name: str):
    return (
        db.query(Ingredient)
        .filter(_ACTIVE, func.lower(Ingredient.name) == name.lower().strip())
        .first()
    )


def fuzzy_match_ingredient(db: Session, name: str) -> tuple:
    active = db.query(Ingredient).filter(_ACTIVE).all()
    return fuzzy_match(active, name)


def create_ingredient(db: Session, name: str, unit: str) -> Ingredient:
    deleted = (
        db.query(Ingredient)
        .filter(
            Ingredient.is_deleted == True,  # noqa: E712
            func.lower(Ingredient.name) == name.strip().lower(),
        )
        .first()
    )
    if deleted:
        deleted.is_deleted = False
        deleted.current_stock = 0.0
        db.flush()
        return deleted

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
    ingredient = db.query(Ingredient).filter(_ACTIVE, Ingredient.id == ingredient_id).first()
    if ingredient is None:
        raise ValueError(f"Ingredient {ingredient_id} not found")
    ingredient.current_stock = current_stock
    ingredient.reorder_threshold = reorder_threshold
    db.flush()
    return ingredient


def delete_ingredient(db: Session, ingredient_id: int) -> None:
    ingredient = db.query(Ingredient).filter(_ACTIVE, Ingredient.id == ingredient_id).first()
    if ingredient is None:
        raise ValueError(f"Ingredient {ingredient_id} not found")
    ingredient.is_deleted = True
    db.flush()
