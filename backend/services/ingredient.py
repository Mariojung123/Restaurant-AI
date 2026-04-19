import difflib

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import Ingredient


def find_ingredient_by_name(db: Session, name: str):
    return (
        db.query(Ingredient)
        .filter(func.lower(Ingredient.name) == name.lower().strip())
        .first()
    )


def fuzzy_match_ingredient(db: Session, name: str) -> tuple:
    """Return best-matching Ingredient via SequenceMatcher. Returns (None, 0.0) if below 0.7."""
    ingredients = db.query(Ingredient).all()
    if not ingredients:
        return (None, 0.0)

    best_score = 0.0
    best_match = None
    for ingredient in ingredients:
        score = difflib.SequenceMatcher(
            None, name.lower().strip(), ingredient.name.lower().strip()
        ).ratio()
        if score > best_score:
            best_score = score
            best_match = ingredient

    if best_score >= 0.7:
        return (best_match, best_score)
    return (None, 0.0)


def create_ingredient(db: Session, name: str, unit: str) -> Ingredient:
    ingredient = Ingredient(name=name.strip(), unit=unit or "unit", current_stock=0.0)
    db.add(ingredient)
    db.flush()
    return ingredient
