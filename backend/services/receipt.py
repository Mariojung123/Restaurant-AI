from datetime import datetime

from sqlalchemy.orm import Session

from models.database import Ingredient, Recipe, RecipeIngredient, SalesLog
from services.fuzzy_match import fuzzy_match


def fuzzy_match_recipe(db: Session, name: str) -> tuple:
    return fuzzy_match(db.query(Recipe).all(), name)


def process_receipt_items(
    items: list[dict], sale_date: str | None, db: Session
) -> tuple[list[dict], int]:
    """Create SalesLogs and deduct ingredient stock. Caller must db.commit()."""
    if sale_date:
        try:
            sold_at = datetime.strptime(sale_date, "%Y-%m-%d")
        except ValueError:
            sold_at = datetime.utcnow()
    else:
        sold_at = datetime.utcnow()

    results = []
    skipped_count = 0

    for item in items:
        recipe_id = item.get("recipe_id")
        if not recipe_id:
            skipped_count += 1
            continue

        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            skipped_count += 1
            continue

        quantity = int(item.get("quantity", 1))
        total_price = item.get("total_price")

        sales_log = SalesLog(
            recipe_id=recipe_id,
            quantity=quantity,
            total_price=total_price,
            sold_at=sold_at,
        )
        db.add(sales_log)
        db.flush()

        recipe_ingredients = (
            db.query(RecipeIngredient)
            .filter(RecipeIngredient.recipe_id == recipe_id)
            .all()
        )

        deducted = 0
        for ri in recipe_ingredients:
            if ri.quantity is None:
                continue
            ingredient = db.query(Ingredient).filter(Ingredient.id == ri.ingredient_id).first()
            if ingredient:
                ingredient.current_stock -= ri.quantity * quantity
                deducted += 1

        db.flush()

        results.append(
            {
                "name": item.get("name", ""),
                "quantity": quantity,
                "total_price": total_price,
                "recipe_id": recipe_id,
                "sales_log_id": sales_log.id,
                "ingredients_deducted": deducted,
            }
        )

    return results, skipped_count
