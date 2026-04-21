from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import Ingredient, Recipe, RecipeIngredient, SalesLog
from services.constants import DEFAULT_RECIPE_TOOL_UNIT, DEFAULT_UNIT
from services.ingredient import FUZZY_MATCH_THRESHOLD, create_ingredient, fuzzy_match_ingredient


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
            ingredient = create_ingredient(db, item["name"], item.get("unit", DEFAULT_UNIT))
            created += 1
        else:
            linked += 1

        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=item.get("quantity"),
                unit=item.get("unit", DEFAULT_UNIT),
                quantity_display=item.get("quantity_display"),
            )
        )

    return {
        "id": recipe.id,
        "name": recipe.name,
        "ingredients_linked": linked,
        "ingredients_created": created,
    }


def register_recipe_from_tool(
    db: Session,
    name: str,
    price: float,
    items: list[dict],
) -> dict:
    """Resolve ingredient names via fuzzy match, then delegate to save_recipe_core.

    items: list of dicts with keys: name, quantity, unit, quantity_display.
    Caller must db.commit() after this returns.
    """
    resolved = []
    for item in items:
        match, score = fuzzy_match_ingredient(db, item["name"])
        ingredient = match if (match and score >= FUZZY_MATCH_THRESHOLD) else None
        resolved.append(
            {
                "ingredient": ingredient,
                "name": item["name"],
                "quantity": item.get("quantity"),
                "unit": item.get("unit", DEFAULT_RECIPE_TOOL_UNIT),
                "quantity_display": item.get("quantity_display", str(item.get("quantity", ""))),
            }
        )
    return save_recipe_core(db, name=name, description=None, price=price, resolved_items=resolved)


def get_recipe_detail(db: Session, recipe_id: int) -> dict | None:
    """Return recipe + ingredients as a plain dict, or None if not found."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        return None
    ingredients = [
        {
            "link_id": link.id,
            "ingredient_id": link.ingredient_id,
            "name": link.ingredient.name,
            "quantity": link.quantity,
            "unit": link.unit,
            "quantity_display": link.quantity_display,
        }
        for link in recipe.ingredient_links
    ]
    return {
        "id": recipe.id,
        "name": recipe.name,
        "description": recipe.description,
        "price": recipe.price,
        "ingredients": ingredients,
    }


def replace_recipe_ingredients(db: Session, recipe_id: int, items: list[dict]) -> None:
    db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()
    for item in items:
        ingredient = db.query(Ingredient).filter(Ingredient.id == item["ingredient_id"]).first()
        if ingredient is None:
            raise ValueError(f"Ingredient not found: {item['ingredient_id']}")
        db.add(RecipeIngredient(
            recipe_id=recipe_id,
            ingredient_id=ingredient.id,
            quantity=item.get("quantity"),
            unit=item.get("unit", DEFAULT_UNIT),
            quantity_display=item.get("quantity_display"),
        ))


def update_recipe_fields(
    db: Session, recipe_id: int, name: str, description: str | None, price: float
) -> Recipe | None:
    """Update name/description/price. Returns updated Recipe or None if not found.

    Raises ValueError if name conflicts with another recipe.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        return None
    duplicate = (
        db.query(Recipe)
        .filter(Recipe.name == name, Recipe.id != recipe_id)
        .first()
    )
    if duplicate:
        raise ValueError(f"Recipe name already exists: {name}")
    recipe.name = name
    recipe.description = description
    recipe.price = price
    db.flush()
    return recipe


def delete_recipe_by_id(db: Session, recipe_id: int) -> bool:
    """Delete recipe. Returns False if not found."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        return False
    db.delete(recipe)
    return True


def create_recipe_with_links(
    db: Session,
    name: str,
    description: str | None,
    price: float,
    ingredients: list,
) -> Recipe:
    """Create recipe and ingredient links. Raises ValueError for invalid ingredient id."""
    recipe = Recipe(name=name, description=description, price=price)
    db.add(recipe)
    db.flush()

    for link in ingredients:
        ingredient = db.query(Ingredient).filter(Ingredient.id == link.ingredient_id).first()
        if ingredient is None:
            raise ValueError(f"Ingredient not found: {link.ingredient_id}")
        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=link.ingredient_id,
                quantity=link.quantity,
                unit=link.unit,
                quantity_display=link.quantity_display,
            )
        )

    db.flush()
    return recipe


def record_recipe_sale(
    db: Session,
    recipe_id: int,
    quantity: int,
    total_price: float | None,
) -> SalesLog:
    """Create a SalesLog for an existing recipe. Raises ValueError if missing recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        raise ValueError("Recipe not found")

    sale = SalesLog(
        recipe_id=recipe_id,
        quantity=quantity,
        total_price=total_price,
    )
    db.add(sale)
    db.flush()
    return sale
