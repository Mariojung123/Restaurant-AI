import json
from datetime import datetime
from unittest.mock import patch

import pytest

from models.database import Ingredient, Recipe, RecipeIngredient, SalesLog
from services.receipt import fuzzy_match_recipe, process_receipt_items


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_receipt_json(items, sale_date="2024-05-10"):
    return json.dumps({"sale_date": sale_date, "items": items})


def _post_preview(client, content=b"fake-image", content_type="image/jpeg"):
    return client.post(
        "/api/vision/receipt/preview",
        files={"file": ("receipt.jpg", content, content_type)},
    )


def _make_recipe_with_ingredient(db_session, recipe_name, ingredient_name, qty=0.5):
    ingredient = Ingredient(name=ingredient_name, unit="kg", current_stock=10.0)
    db_session.add(ingredient)
    db_session.flush()

    recipe = Recipe(name=recipe_name, price=18.0)
    db_session.add(recipe)
    db_session.flush()

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=qty,
        unit="kg",
    )
    db_session.add(ri)
    db_session.flush()
    return recipe, ingredient


# ── preview endpoint tests ────────────────────────────────────────────────────

def test_preview_returns_fuzzy_match(client, db_session):
    recipe = Recipe(name="rcp-grilled-chicken-99", price=18.0)
    db_session.add(recipe)
    db_session.flush()

    mock_resp = _make_receipt_json(
        [{"name": "rcp-grilled-chicken-99", "quantity": 3,
          "unit_price": 18.0, "total_price": 54.0}]
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        resp = _post_preview(client)

    assert resp.status_code == 200
    body = resp.json()
    item = body["items"][0]
    assert item["suggested_match"] is not None
    assert item["suggested_match"]["name"] == "rcp-grilled-chicken-99"
    assert item["match_score"] >= 0.7


def test_preview_no_match_below_threshold(client, db_session):
    recipe = Recipe(name="rcp-pasta-carbonara-99", price=16.0)
    db_session.add(recipe)
    db_session.flush()

    mock_resp = _make_receipt_json(
        [{"name": "xyzxyzxyz888abc", "quantity": 1,
          "unit_price": None, "total_price": None}]
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        resp = _post_preview(client)

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["suggested_match"] is None
    assert item["match_score"] == 0.0


def test_preview_no_db_writes(client, db_session):
    sales_before = db_session.query(SalesLog).count()

    mock_resp = _make_receipt_json(
        [{"name": "rcp-no-write-item-99", "quantity": 2,
          "unit_price": 10.0, "total_price": 20.0}]
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        _post_preview(client)

    assert db_session.query(SalesLog).count() == sales_before


def test_preview_duplicate_warning(client, db_session):
    recipe = Recipe(name="rcp-dup-burger-99", price=12.0)
    db_session.add(recipe)
    db_session.flush()

    existing_log = SalesLog(
        recipe_id=recipe.id,
        quantity=1,
        total_price=12.0,
        sold_at=datetime(2024, 5, 10, 12, 0, 0),
    )
    db_session.add(existing_log)
    db_session.flush()

    mock_resp = _make_receipt_json(
        [{"name": "rcp-dup-burger-99", "quantity": 1,
          "unit_price": 12.0, "total_price": 12.0}],
        sale_date="2024-05-10",
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        resp = _post_preview(client)

    assert resp.status_code == 200
    assert resp.json()["duplicate_warning"] is True


def test_preview_rejects_unsupported_type(client):
    resp = _post_preview(client, content_type="application/pdf")
    assert resp.status_code == 400


def test_preview_rejects_empty_file(client):
    resp = _post_preview(client, content=b"")
    assert resp.status_code == 400


def test_preview_malformed_json_returns_422(client):
    with patch("services.vision_common.parse_image_with_claude", return_value="not json"):
        resp = _post_preview(client)
    assert resp.status_code == 422
    assert "non-JSON" in resp.json()["detail"]


def test_preview_strips_markdown_fences(client, db_session):
    inner = json.dumps({
        "sale_date": "2024-05-10",
        "items": [{"name": "rcp-steak-99", "quantity": 2,
                   "unit_price": 30.0, "total_price": 60.0}],
    })
    raw_with_fences = f"```json\n{inner}\n```"
    with patch("services.vision_common.parse_image_with_claude", return_value=raw_with_fences):
        resp = _post_preview(client)
    assert resp.status_code == 200
    assert resp.json()["sale_date"] == "2024-05-10"


# ── confirm endpoint tests ────────────────────────────────────────────────────

def test_confirm_saves_sales_and_deducts_stock(client, db_session):
    recipe, ingredient = _make_recipe_with_ingredient(
        db_session, "rct-chicken-rice-99", "rct-chicken-breast-99", qty=0.3
    )

    payload = {
        "sale_date": "2024-05-10",
        "items": [
            {
                "name": "cnf-chicken-rice-99",
                "quantity": 3,
                "unit_price": 15.0,
                "total_price": 45.0,
                "recipe_id": recipe.id,
                "include": True,
            }
        ],
    }
    resp = client.post("/api/vision/receipt/confirm", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items_processed"] == 1
    assert body["items_skipped"] == 0
    assert body["items"][0]["ingredients_deducted"] == 1

    db_session.expire_all()
    updated = db_session.query(Ingredient).filter_by(id=ingredient.id).first()
    assert abs(updated.current_stock - (10.0 - 0.3 * 3)) < 0.001

    log = db_session.query(SalesLog).filter_by(recipe_id=recipe.id).first()
    assert log is not None
    assert log.quantity == 3
    assert log.total_price == 45.0


def test_confirm_skips_excluded_items(client, db_session):
    recipe = Recipe(name="cnf-excluded-dish-99", price=10.0)
    db_session.add(recipe)
    db_session.flush()

    sales_before = db_session.query(SalesLog).count()

    payload = {
        "sale_date": "2024-05-10",
        "items": [
            {
                "name": "cnf-excluded-dish-99",
                "quantity": 2,
                "unit_price": 10.0,
                "total_price": 20.0,
                "recipe_id": recipe.id,
                "include": False,
            }
        ],
    }
    resp = client.post("/api/vision/receipt/confirm", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items_processed"] == 0
    assert body["items_skipped"] == 1
    assert db_session.query(SalesLog).count() == sales_before


def test_confirm_skips_null_recipe_id(client, db_session):
    payload = {
        "sale_date": "2024-05-10",
        "items": [
            {
                "name": "unknown-dish",
                "quantity": 1,
                "unit_price": 10.0,
                "total_price": 10.0,
                "recipe_id": None,
                "include": True,
            }
        ],
    }
    resp = client.post("/api/vision/receipt/confirm", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items_processed"] == 0
    assert body["items_skipped"] == 1


def test_confirm_all_excluded_returns_zero(client, db_session):
    payload = {
        "sale_date": "2024-05-11",
        "items": [
            {
                "name": "cnf-nobody-dish-99",
                "quantity": 1,
                "unit_price": None,
                "total_price": None,
                "recipe_id": None,
                "include": False,
            }
        ],
    }
    resp = client.post("/api/vision/receipt/confirm", json=payload)

    assert resp.status_code == 200
    assert resp.json()["items_processed"] == 0


def test_confirm_null_recipe_ingredient_skips_deduction(client, db_session):
    recipe = Recipe(name="cnf-vague-dish-99", price=12.0)
    db_session.add(recipe)
    db_session.flush()

    ingredient = Ingredient(name="cnf-vague-ing-99", unit="unit", current_stock=5.0)
    db_session.add(ingredient)
    db_session.flush()

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=None,
        unit="unit",
        quantity_display="조금",
    )
    db_session.add(ri)
    db_session.flush()

    payload = {
        "sale_date": "2024-05-12",
        "items": [
            {
                "name": "cnf-vague-dish-99",
                "quantity": 2,
                "unit_price": 12.0,
                "total_price": 24.0,
                "recipe_id": recipe.id,
                "include": True,
            }
        ],
    }
    resp = client.post("/api/vision/receipt/confirm", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["ingredients_deducted"] == 0

    db_session.expire_all()
    ing = db_session.query(Ingredient).filter_by(id=ingredient.id).first()
    assert ing.current_stock == 5.0


def test_confirm_allows_negative_stock(client, db_session):
    recipe, ingredient = _make_recipe_with_ingredient(
        db_session, "cnf-low-stock-dish-99", "cnf-low-stock-ing-99", qty=5.0
    )
    ingredient.current_stock = 2.0
    db_session.flush()

    payload = {
        "sale_date": "2024-05-13",
        "items": [
            {
                "name": "cnf-low-stock-dish-99",
                "quantity": 1,
                "unit_price": 20.0,
                "total_price": 20.0,
                "recipe_id": recipe.id,
                "include": True,
            }
        ],
    }
    resp = client.post("/api/vision/receipt/confirm", json=payload)

    assert resp.status_code == 200

    db_session.expire_all()
    ing = db_session.query(Ingredient).filter_by(id=ingredient.id).first()
    assert ing.current_stock == -3.0


# ── service unit tests ────────────────────────────────────────────────────────

def test_fuzzy_match_recipe_exact(db_session):
    recipe = Recipe(name="rcp-beef-stew-99", price=20.0)
    db_session.add(recipe)
    db_session.flush()

    match, score = fuzzy_match_recipe(db_session, "rcp-beef-stew-99")
    assert match is not None
    assert score == 1.0


def test_fuzzy_match_recipe_partial(db_session):
    recipe = Recipe(name="rcp-mozzarella-pasta-99", price=16.0)
    db_session.add(recipe)
    db_session.flush()

    match, score = fuzzy_match_recipe(db_session, "rcp-mozz-pasta-99")
    assert match is not None
    assert score >= 0.7


def test_fuzzy_match_recipe_no_match(db_session):
    recipe = Recipe(name="rcp-olive-chicken-99", price=15.0)
    db_session.add(recipe)
    db_session.flush()

    match, score = fuzzy_match_recipe(db_session, "xyzxyzxyz999abc")
    assert match is None
    assert score == 0.0


def test_process_receipt_items_creates_log(db_session):
    recipe, ingredient = _make_recipe_with_ingredient(
        db_session, "proc-salmon-rice-99", "proc-salmon-99", qty=0.2
    )

    items = [
        {
            "name": "proc-salmon-rice-99",
            "quantity": 2,
            "total_price": 36.0,
            "recipe_id": recipe.id,
        }
    ]
    results, skipped = process_receipt_items(items, "2024-05-10", db_session)
    db_session.flush()

    assert len(results) == 1
    assert skipped == 0
    assert results[0]["ingredients_deducted"] == 1
    assert results[0]["sales_log_id"] is not None

    db_session.expire_all()
    ing = db_session.query(Ingredient).filter_by(id=ingredient.id).first()
    assert abs(ing.current_stock - (10.0 - 0.2 * 2)) < 0.001


def test_process_receipt_items_skips_null_recipe(db_session):
    items = [
        {
            "name": "unknown-item",
            "quantity": 1,
            "total_price": 10.0,
            "recipe_id": None,
        }
    ]
    results, skipped = process_receipt_items(items, "2024-05-10", db_session)

    assert len(results) == 0
    assert skipped == 1


def test_process_receipt_items_cross_unit_conversion(db_session):
    """Recipe ingredient in g, ingredient stored in kg — deduction must convert."""
    ingredient = Ingredient(name="uct-flour-99", unit="kg", current_stock=2.0)
    db_session.add(ingredient)
    db_session.flush()

    recipe = Recipe(name="uct-bread-99", price=5.0)
    db_session.add(recipe)
    db_session.flush()

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=500.0,
        unit="g",
    )
    db_session.add(ri)
    db_session.flush()

    items = [{"name": "uct-bread-99", "quantity": 1, "total_price": 5.0, "recipe_id": recipe.id}]
    results, skipped = process_receipt_items(items, "2024-05-10", db_session)
    db_session.flush()

    assert skipped == 0
    db_session.expire_all()
    ing = db_session.query(Ingredient).filter_by(id=ingredient.id).first()
    # 500g = 0.5kg deducted from 2.0kg → 1.5kg
    assert abs(ing.current_stock - 1.5) < 1e-6


def test_process_receipt_items_cross_unit_volume(db_session):
    """Recipe ingredient in mL, ingredient stored in L."""
    ingredient = Ingredient(name="uct-oil-99", unit="L", current_stock=1.0)
    db_session.add(ingredient)
    db_session.flush()

    recipe = Recipe(name="uct-salad-99", price=8.0)
    db_session.add(recipe)
    db_session.flush()

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=250.0,
        unit="ml",
    )
    db_session.add(ri)
    db_session.flush()

    items = [{"name": "uct-salad-99", "quantity": 2, "total_price": 16.0, "recipe_id": recipe.id}]
    results, skipped = process_receipt_items(items, "2024-05-10", db_session)
    db_session.flush()

    assert skipped == 0
    db_session.expire_all()
    ing = db_session.query(Ingredient).filter_by(id=ingredient.id).first()
    # 250mL * 2 = 500mL = 0.5L deducted from 1.0L → 0.5L
    assert abs(ing.current_stock - 0.5) < 1e-6


def test_process_receipt_items_null_sale_date(db_session):
    recipe = Recipe(name="proc-no-date-dish-99", price=10.0)
    db_session.add(recipe)
    db_session.flush()

    items = [
        {
            "name": "proc-no-date-dish-99",
            "quantity": 1,
            "total_price": 10.0,
            "recipe_id": recipe.id,
        }
    ]
    results, skipped = process_receipt_items(items, None, db_session)
    db_session.flush()

    assert len(results) == 1
    log = db_session.query(SalesLog).filter_by(id=results[0]["sales_log_id"]).first()
    assert log is not None
