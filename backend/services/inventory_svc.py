from sqlalchemy.orm import Session

from models.database import Ingredient, InventoryLog


def record_inventory_change(
    db: Session,
    ingredient_id: int,
    change_type: str,
    quantity: float,
    unit_cost: float | None = None,
    supplier: str | None = None,
    note: str | None = None,
) -> tuple[InventoryLog, float]:
    """Create an InventoryLog and update ingredient stock. Caller must db.commit().

    Returns (log, new_current_stock). Raises ValueError if ingredient not found.
    """
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient is None:
        raise ValueError(f"Ingredient not found: {ingredient_id}")

    log = InventoryLog(
        ingredient_id=ingredient_id,
        change_type=change_type,
        quantity=quantity,
        unit_cost=unit_cost,
        supplier=supplier,
        note=note,
    )
    ingredient.current_stock += quantity
    db.add(log)
    db.flush()
    return log, ingredient.current_stock
