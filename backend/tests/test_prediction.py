from datetime import datetime, timedelta, timezone

import pytest

from models.database import Ingredient, Recipe, RecipeIngredient, SalesLog
from services.prediction import forecast_ingredient, forecast_all


# ── helpers ───────────────────────────────────────────────────────────────────

def _ingredient(name, stock, threshold=0.0, unit="kg"):
    return Ingredient(name=name, unit=unit, current_stock=stock, reorder_threshold=threshold)


def _recipe(name):
    return Recipe(name=name, price=0.0)


def _sale(recipe, qty, days_ago):
    sold_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return SalesLog(recipe_id=recipe.id, quantity=qty, sold_at=sold_at)


# ── forecast_ingredient ───────────────────────────────────────────────────────

def test_prd_no_sales_returns_none_depletion(db_session):
    ing = _ingredient("prd-tomato", stock=10.0)
    db_session.add(ing)
    db_session.flush()

    result = forecast_ingredient(db_session, ing, lookback_days=14)

    assert result.daily_consumption == 0.0
    assert result.days_remaining is None
    assert result.depletion_date is None


def test_prd_basic_depletion_calculation(db_session):
    ing = _ingredient("prd-onion", stock=14.0)
    recipe = _recipe("prd-soup")
    db_session.add_all([ing, recipe])
    db_session.flush()

    link = RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing.id, quantity=1.0, unit="kg")
    db_session.add(link)
    db_session.flush()

    # 14 sales over 14 days → daily consumption = 1.0
    for i in range(14):
        db_session.add(_sale(recipe, qty=1, days_ago=i))
    db_session.flush()

    result = forecast_ingredient(db_session, ing, lookback_days=14)

    assert abs(result.daily_consumption - 1.0) < 0.01
    assert result.days_remaining is not None
    assert abs(result.days_remaining - 14.0) < 0.1
    assert result.depletion_date is not None


def test_prd_needs_reorder_when_below_threshold(db_session):
    ing = _ingredient("prd-garlic", stock=2.0, threshold=5.0)
    db_session.add(ing)
    db_session.flush()

    result = forecast_ingredient(db_session, ing)

    assert result.needs_reorder is True


def test_prd_no_reorder_when_above_threshold(db_session):
    ing = _ingredient("prd-butter", stock=10.0, threshold=5.0)
    db_session.add(ing)
    db_session.flush()

    result = forecast_ingredient(db_session, ing)

    assert result.needs_reorder is False


def test_prd_null_quantity_in_recipe_ingredient_skipped(db_session):
    """RecipeIngredient.quantity is nullable — must not cause TypeError."""
    ing = _ingredient("prd-pepper", stock=5.0)
    recipe = _recipe("prd-steak")
    db_session.add_all([ing, recipe])
    db_session.flush()

    link = RecipeIngredient(
        recipe_id=recipe.id, ingredient_id=ing.id, quantity=None, unit="pinch"
    )
    db_session.add(link)
    db_session.flush()

    db_session.add(_sale(recipe, qty=3, days_ago=1))
    db_session.flush()

    result = forecast_ingredient(db_session, ing, lookback_days=14)

    assert result.daily_consumption == 0.0
    assert result.days_remaining is None


def test_prd_sales_outside_lookback_ignored(db_session):
    ing = _ingredient("prd-cream", stock=10.0)
    recipe = _recipe("prd-pasta")
    db_session.add_all([ing, recipe])
    db_session.flush()

    link = RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing.id, quantity=1.0, unit="L")
    db_session.add(link)
    db_session.flush()

    db_session.add(_sale(recipe, qty=100, days_ago=30))
    db_session.flush()

    result = forecast_ingredient(db_session, ing, lookback_days=14)

    assert result.daily_consumption == 0.0


# ── forecast_all ─────────────────────────────────────────────────────────────

def test_prd_forecast_all_returns_all_ingredients(db_session):
    db_session.add_all([
        _ingredient("prd-milk", stock=5.0),
        _ingredient("prd-flour", stock=3.0),
    ])
    db_session.flush()

    before_count = len(forecast_all(db_session))
    # both prd- ingredients should be included (at minimum)
    assert before_count >= 2


# ── GET /api/inventory/forecast endpoint ─────────────────────────────────────

def test_prd_forecast_endpoint_returns_list(client, db_session):
    db_session.add(_ingredient("prd-egg", stock=24.0, threshold=10.0))
    db_session.flush()

    resp = client.get("/api/inventory/forecast")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = [d["ingredient_name"] for d in data]
    assert "prd-egg" in names


def test_prd_forecast_endpoint_fields_present(client, db_session):
    db_session.add(_ingredient("prd-salt", stock=1.0, threshold=2.0))
    db_session.flush()

    resp = client.get("/api/inventory/forecast")
    assert resp.status_code == 200

    item = next(d for d in resp.json() if d["ingredient_name"] == "prd-salt")
    assert "ingredient_id" in item
    assert "current_stock" in item
    assert "daily_consumption" in item
    assert "days_remaining" in item
    assert "depletion_date" in item
    assert "needs_reorder" in item
    assert item["needs_reorder"] is True
