from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import Ingredient, Recipe, RecipeIngredient
from services.ingredient import create_ingredient


def save_recipe_core(
    db: Session,
    name: str,
    description,
    price: float,
    resolved_items: list[dict],
) -> dict:
    """Create Recipe + RecipeIngredient rows from pre-resolved items.

    resolved_items: list of dicts with keys:
        ingredient (Ingredient | None), name, quantity, unit, quantity_display

    Raises ValueError if recipe name already exists.
    Caller must db.commit() after this returns.
    """
    existing = (
        db.query(Recipe)
        .filter(func.lower(Recipe.name) == name.lower().strip())
        .first()
    )
    if existing:
        raise ValueError(f"'{name}' recipe already exists")

    recipe = Recipe(name=name, description=description, price=price)
    db.add(recipe)
    db.flush()

    linked = 0
    created = 0
    for item in resolved_items:
        ingredient: Ingredient | None = item.get("ingredient")
        if ingredient is None:
            ingredient = create_ingredient(db, item["name"], item.get("unit", "unit"))
            created += 1
        else:
            linked += 1

        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=item.get("quantity"),
                unit=item.get("unit", "unit"),
                quantity_display=item.get("quantity_display"),
            )
        )

    return {
        "id": recipe.id,
        "name": recipe.name,
        "ingredients_linked": linked,
        "ingredients_created": created,
    }
