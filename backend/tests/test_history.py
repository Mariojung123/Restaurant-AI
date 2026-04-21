from datetime import datetime, timedelta, timezone

import pytest

from models.database import Ingredient, Recipe, RecipeIngredient, SalesLog
from services.prediction import daily_usage_history


# ── helpers ───────────────────────────────────────────────────────────────────

def _ingredient(name, stock=10.0):
    return Ingredient(name=name, unit="kg", current_stock=stock, reorder_threshold=0.0)


def _recipe(name):
    return Recipe(name=name, price=0.0)


def _sale(recipe, qty, days_ago):
    sold_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return SalesLog(recipe_id=recipe.id, quantity=qty, sold_at=sold_at)


# ── daily_usage_history service ───────────────────────────────────────────────

def test_hst_empty_returns_all_zero_days(db_session):
    ing = _ingredient("hst-flour")
    db_session.add(ing)
    db_session.flush()

    result = daily_usage_history(db_session, ing.id, lookback_days=7)

    assert len(result) == 7
    assert all(r.amount == 0.0 for r in result)


def test_hst_dates_are_chronological(db_session):
    ing = _ingredient("hst-sugar")
    db_session.add(ing)
    db_session.flush()

    result = daily_usage_history(db_session, ing.id, lookback_days=7)

    dates = [r.date for r in result]
    assert dates == sorted(dates)


def test_hst_sale_appears_on_correct_day(db_session):
    ing = _ingredient("hst-salt")
    recipe = _recipe("hst-soup")
    db_session.add_all([ing, recipe])
    db_session.flush()

    link = RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing.id, quantity=2.0, unit="kg")
    db_session.add(link)
    db_session.flush()

    # 3 sold yesterday → 3 * 2.0 = 6.0 kg used
    db_session.add(_sale(recipe, qty=3, days_ago=1))
    db_session.flush()

    result = daily_usage_history(db_session, ing.id, lookback_days=7)

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    day = next(r for r in result if r.date == yesterday)
    assert abs(day.amount - 6.0) < 0.01


def test_hst_null_recipe_ingredient_quantity_skipped(db_session):
    ing = _ingredient("hst-pepper")
    recipe = _recipe("hst-steak")
    db_session.add_all([ing, recipe])
    db_session.flush()

    link = RecipeIngredient(
        recipe_id=recipe.id, ingredient_id=ing.id, quantity=None, unit="pinch"
    )
    db_session.add(link)
    db_session.flush()

    db_session.add(_sale(recipe, qty=5, days_ago=1))
    db_session.flush()

    result = daily_usage_history(db_session, ing.id, lookback_days=7)

    assert all(r.amount == 0.0 for r in result)


def test_hst_sales_outside_window_ignored(db_session):
    ing = _ingredient("hst-oil")
    recipe = _recipe("hst-fries")
    db_session.add_all([ing, recipe])
    db_session.flush()

    link = RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing.id, quantity=1.0, unit="L")
    db_session.add(link)
    db_session.flush()

    db_session.add(_sale(recipe, qty=100, days_ago=30))
    db_session.flush()

    result = daily_usage_history(db_session, ing.id, lookback_days=7)

    assert all(r.amount == 0.0 for r in result)


def test_hst_multiple_sales_same_day_summed(db_session):
    ing = _ingredient("hst-butter")
    recipe = _recipe("hst-cake")
    db_session.add_all([ing, recipe])
    db_session.flush()

    link = RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing.id, quantity=1.0, unit="kg")
    db_session.add(link)
    db_session.flush()

    db_session.add(_sale(recipe, qty=2, days_ago=2))
    db_session.add(_sale(recipe, qty=3, days_ago=2))
    db_session.flush()

    result = daily_usage_history(db_session, ing.id, lookback_days=7)

    two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    day = next(r for r in result if r.date == two_days_ago)
    assert abs(day.amount - 5.0) < 0.01


# ── GET /api/inventory/history/{ingredient_id} endpoint ──────────────────────

def test_hst_endpoint_404_unknown_ingredient(client):
    resp = client.get("/api/inventory/history/99999")
    assert resp.status_code == 404


def test_hst_endpoint_returns_list_with_correct_length(client, db_session):
    ing = _ingredient("hst-cream")
    db_session.add(ing)
    db_session.flush()

    resp = client.get(f"/api/inventory/history/{ing.id}?lookback_days=7")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 7


def test_hst_endpoint_fields_present(client, db_session):
    ing = _ingredient("hst-yeast")
    db_session.add(ing)
    db_session.flush()

    resp = client.get(f"/api/inventory/history/{ing.id}")

    assert resp.status_code == 200
    row = resp.json()[0]
    assert "date" in row
    assert "amount" in row
