import difflib

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import Ingredient, InventoryLog


def _find_ingredient_by_name(db: Session, name: str):
    return (
        db.query(Ingredient)
        .filter(func.lower(Ingredient.name) == name.lower().strip())
        .first()
    )


def fuzzy_match_ingredient(db: Session, name: str) -> tuple:
    """Return best-matching Ingredient via SequenceMatcher. Threshold 0.7."""
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


def _create_ingredient(db: Session, name: str, unit: str) -> Ingredient:
    ingredient = Ingredient(name=name.strip(), unit=unit or "unit", current_stock=0.0)
    db.add(ingredient)
    db.flush()
    return ingredient


def _create_log(
    db: Session,
    ingredient: Ingredient,
    quantity: float,
    unit_cost,
    supplier,
) -> InventoryLog:
    log = InventoryLog(
        ingredient_id=ingredient.id,
        change_type="delivery",
        quantity=quantity,
        unit_cost=unit_cost,
        supplier=supplier,
        note="Auto-created from invoice scan",
    )
    ingredient.current_stock += quantity
    db.add(log)
    db.flush()
    return log


def process_invoice_items(items: list[dict], supplier, db: Session) -> list[dict]:
    """Match or create Ingredients for each line item and create InventoryLogs.

    If item has ingredient_id, use that directly (confirm flow).
    Caller must call db.commit() after this returns.
    """
    results = []
    for item in items:
        name = item["name"]
        quantity = float(item["quantity"])
        unit = item.get("unit") or "unit"
        unit_price = item.get("unit_price")
        ingredient_id = item.get("ingredient_id")

        ingredient = None
        if ingredient_id:
            ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

        if not ingredient:
            ingredient = _find_ingredient_by_name(db, name)

        action = "matched" if ingredient else "created"
        if not ingredient:
            ingredient = _create_ingredient(db, name, unit)

        log = _create_log(db, ingredient, quantity, unit_price, supplier)
        results.append(
            {
                "name": name,
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
                "action": action,
                "ingredient_id": ingredient.id,
                "inventory_log_id": log.id,
            }
        )
    return results
