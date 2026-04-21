import logging

logger = logging.getLogger(__name__)

# (dimension, factor_to_base_unit)  — base: g for mass, mL for volume
_UNIT_TABLE: dict[str, tuple[str, float]] = {
    "g":      ("mass",   1.0),
    "kg":     ("mass",   1000.0),
    "oz":     ("mass",   28.3495),
    "lb":     ("mass",   453.592),
    "ml":     ("volume", 1.0),
    "l":      ("volume", 1000.0),
    "tsp":    ("volume", 4.92892),
    "tbsp":   ("volume", 14.7868),
    "cup":    ("volume", 240.0),
    "fl oz":  ("volume", 29.5735),
}


def convert_quantity(quantity: float, from_unit: str, to_unit: str) -> float:
    """Return quantity converted from from_unit to to_unit.

    Falls back to raw quantity (with warning) when units are unknown or
    dimensionally incompatible (e.g. g → L).
    """
    if from_unit == to_unit:
        return quantity

    from_key = from_unit.strip().lower()
    to_key = to_unit.strip().lower()

    if from_key == to_key:
        return quantity

    from_info = _UNIT_TABLE.get(from_key)
    to_info = _UNIT_TABLE.get(to_key)

    if from_info is None or to_info is None:
        logger.warning(
            "Unknown unit in conversion: from=%r to=%r — using raw quantity",
            from_unit,
            to_unit,
        )
        return quantity

    from_dim, from_factor = from_info
    to_dim, to_factor = to_info

    if from_dim != to_dim:
        logger.warning(
            "Incompatible unit dimensions: %r (%s) → %r (%s) — using raw quantity",
            from_unit,
            from_dim,
            to_unit,
            to_dim,
        )
        return quantity

    return quantity * from_factor / to_factor
