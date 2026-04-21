"""Tests for ingredient PATCH and DELETE endpoints.

Prefix: inv-  (unique to this file — no collision with pvw-, cnf-, fuz-, rct-, cr-, rec-)
"""

import pytest

from models.database import Ingredient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_ingredient(db_session, name: str, unit: str = "kg") -> Ingredient:
    ingredient = Ingredient(
        name=name,
        unit=unit,
        current_stock=10.0,
        reorder_threshold=2.0,
    )
    db_session.add(ingredient)
    db_session.flush()
    return ingredient


# ---------------------------------------------------------------------------
# PATCH /api/inventory/ingredients/{ingredient_id}
# ---------------------------------------------------------------------------

def test_patch_ingredient_success(client, db_session):
    """PATCH updates current_stock and reorder_threshold and returns IngredientOut."""
    ingredient = _create_ingredient(db_session, "inv-tomato")

    response = client.patch(
        f"/api/inventory/ingredients/{ingredient.id}",
        json={"current_stock": 25.5, "reorder_threshold": 5.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == ingredient.id
    assert body["name"] == "inv-tomato"
    assert body["current_stock"] == 25.5
    assert body["reorder_threshold"] == 5.0


def test_patch_ingredient_partial_update(client, db_session):
    """PATCH with only current_stock leaves reorder_threshold unchanged."""
    ingredient = _create_ingredient(db_session, "inv-onion")
    original_threshold = ingredient.reorder_threshold

    response = client.patch(
        f"/api/inventory/ingredients/{ingredient.id}",
        json={"current_stock": 99.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_stock"] == 99.0
    assert body["reorder_threshold"] == original_threshold


def test_patch_ingredient_not_found(client):
    """PATCH on a non-existent ingredient_id returns 404."""
    response = client.patch(
        "/api/inventory/ingredients/999999",
        json={"current_stock": 1.0, "reorder_threshold": 0.5},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/inventory/ingredients/{ingredient_id}
# ---------------------------------------------------------------------------

def test_delete_ingredient_success(client, db_session):
    """DELETE returns 204 and soft-deletes the row (is_deleted=True, row still in DB)."""
    ingredient = _create_ingredient(db_session, "inv-garlic")
    ingredient_id = ingredient.id

    response = client.delete(f"/api/inventory/ingredients/{ingredient_id}")

    assert response.status_code == 204
    row = db_session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    assert row is not None
    assert row.is_deleted is True


def test_delete_ingredient_restore_on_recreate(client, db_session):
    """Re-creating a soft-deleted ingredient restores original PK with stock reset to 0."""
    ingredient = _create_ingredient(db_session, "inv-pepper")
    original_id = ingredient.id

    client.delete(f"/api/inventory/ingredients/{original_id}")
    db_session.expire_all()

    from services.ingredient import create_ingredient
    restored = create_ingredient(db_session, "inv-pepper", "kg")
    db_session.flush()

    assert restored.id == original_id
    assert restored.is_deleted is False
    assert restored.current_stock == 0.0


def test_delete_ingredient_not_found(client):
    """DELETE on a non-existent ingredient_id returns 404."""
    response = client.delete("/api/inventory/ingredients/999999")

    assert response.status_code == 404
