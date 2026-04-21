from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import Ingredient
from services.constants import DEFAULT_UNIT
from services.fuzzy_match import FUZZY_MATCH_THRESHOLD, fuzzy_match

__all__ = ["FUZZY_MATCH_THRESHOLD", "fuzzy_match_ingredient", "find_ingredient_by_name", "create_ingredient"]


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
