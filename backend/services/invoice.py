from sqlalchemy.orm import Session

from models.database import Ingredient, InventoryLog
from services.constants import AUTO_INVOICE_NOTE, CHANGE_TYPE_DELIVERY, DEFAULT_UNIT
from services.ingredient import create_ingredient, find_ingredient_by_name
from services.unit_convert import convert_quantity

# Re-export so existing callers don't break during transition
from services.ingredient import fuzzy_match_ingredient  # noqa: F401


def _create_log(
    db: Session,
    ingredient: Ingredient,
    raw_quantity: float,
    stock_delta: float,
    unit_cost,
    supplier,
) -> InventoryLog:
    log = InventoryLog(
        ingredient_id=ingredient.id,
        change_type=CHANGE_TYPE_DELIVERY,
        quantity=raw_quantity,
        unit_cost=unit_cost,
        supplier=supplier,
        note=AUTO_INVOICE_NOTE,
    )
    ingredient.current_stock += stock_delta
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
        unit = item.get("unit") or DEFAULT_UNIT
        unit_price = item.get("unit_price")
        ingredient_id = item.get("ingredient_id")

        ingredient = None
        if ingredient_id:
            ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

        if not ingredient:
            ingredient = find_ingredient_by_name(db, name)

        action = "matched" if ingredient else "created"
        if not ingredient:
            ingredient = create_ingredient(db, name, unit)

        stock_delta = convert_quantity(quantity, unit, ingredient.unit)
        log = _create_log(db, ingredient, quantity, stock_delta, unit_price, supplier)
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
