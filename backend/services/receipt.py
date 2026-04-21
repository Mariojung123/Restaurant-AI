import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.database import Ingredient, Recipe, RecipeIngredient, SalesLog
from services.fuzzy_match import fuzzy_match
from services.unit_convert import convert_quantity

logger = logging.getLogger(__name__)


def fuzzy_match_recipe(db: Session, name: str) -> tuple:
    return fuzzy_match(db.query(Recipe).all(), name)


def is_duplicate_sale_date(db: Session, sale_date_str: str) -> bool:
    """Return True if any SalesLog already exists on the given date (YYYY-MM-DD).

    Returns False on invalid date format.
    """
    try:
        sale_dt = datetime.strptime(sale_date_str, "%Y-%m-%d")
    except ValueError:
        logger.warning("Invalid sale_date format '%s', skipping duplicate check", sale_date_str)
        return False
    return (
        db.query(SalesLog)
        .filter(
            SalesLog.sold_at >= sale_dt.replace(hour=0, minute=0, second=0),
            SalesLog.sold_at < sale_dt.replace(hour=23, minute=59, second=59),
        )
        .first()
        is not None
    )


def process_receipt_items(
    items: list[dict], sale_date: str | None, db: Session
) -> tuple[list[dict], int]:
    """Create SalesLogs and deduct ingredient stock. Caller must db.commit()."""
    if sale_date:
        try:
            sold_at = datetime.strptime(sale_date, "%Y-%m-%d")
        except ValueError:
            sold_at = datetime.now(timezone.utc)
    else:
        sold_at = datetime.now(timezone.utc)

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
                delta = convert_quantity(ri.quantity, ri.unit, ingredient.unit)
                ingredient.current_stock -= delta * quantity
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
