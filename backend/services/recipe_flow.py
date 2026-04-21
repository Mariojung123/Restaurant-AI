"""Service helpers for recipe preview/confirm endpoint flows."""

from sqlalchemy.orm import Session

from models.database import Ingredient
from services.claude import parse_recipe_ingredients
from services.constants import DEFAULT_UNIT
from services.ingredient import fuzzy_match_ingredient


def parse_recipe_items(ingredient_text: str) -> list[dict]:
    """Parse natural-language recipe ingredient text via Claude."""
    return parse_recipe_ingredients(ingredient_text)


def build_preview_items(db: Session, parsed_items: list[dict]) -> list[dict]:
    """Build preview rows with fuzzy-match suggestions."""
    preview_items: list[dict] = []
    for item in parsed_items:
        match, score = fuzzy_match_ingredient(db, item["name"])
        preview_items.append(
            {
                "name": item["name"],
                "quantity": item.get("quantity"),
                "unit": item.get("unit", DEFAULT_UNIT),
                "quantity_display": item.get("quantity_display", ""),
                "reasoning": item.get("reasoning", ""),
                "match_score": score,
                "suggested_match": (
                    {"id": match.id, "name": match.name, "unit": match.unit} if match else None
                ),
            }
        )
    return preview_items


def resolve_confirm_items(db: Session, items: list) -> list[dict]:
    """Resolve confirm payload rows to save_recipe_core input format."""
    resolved = []
    for item in items:
        if not item.include:
            continue

        ingredient = None
        if item.ingredient_id is not None:
            ingredient = db.query(Ingredient).filter(Ingredient.is_deleted == False, Ingredient.id == item.ingredient_id).first()  # noqa: E712
            if ingredient is None:
                raise ValueError(f"Ingredient not found: {item.ingredient_id}")

        resolved.append(
            {
                "ingredient": ingredient,
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "quantity_display": item.quantity_display or None,
            }
        )
    return resolved
