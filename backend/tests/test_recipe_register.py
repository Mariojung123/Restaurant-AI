from unittest.mock import patch

import pytest

from models.database import Ingredient, Recipe, RecipeIngredient


PARSED_ITEMS = [
    {
        "name": "salmon fillet",
        "quantity": 200.0,
        "unit": "g",
        "quantity_display": "200g",
        "reasoning": "Standard restaurant portion.",
    },
    {
        "name": "black pepper",
        "quantity": 1.0,
        "unit": "g",
        "quantity_display": "a pinch",
        "reasoning": "A pinch is about 1g.",
    },
]


# ── preview ───────────────────────────────────────────────────────────────────

def test_preview_matched_ingredient(client, db_session):
    db_session.add(Ingredient(name="rec-salmon-fillet-99", unit="kg", current_stock=2.0))
    db_session.flush()

    with patch("routers.recipe.parse_recipe_ingredients", return_value=[
        {
            "name": "rec-salmon-fillet-99",
            "quantity": 200.0,
            "unit": "g",
            "quantity_display": "200g",
            "reasoning": "Standard portion.",
        }
    ]):
        resp = client.post("/api/recipe/preview", json={
            "name": "Test Recipe",
            "price": 20.0,
            "ingredient_text": "rec-salmon-fillet-99 200g",
        })

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Test Recipe"
    item = body["items"][0]
    assert item["suggested_match"] is not None
    assert item["suggested_match"]["name"] == "rec-salmon-fillet-99"
    assert item["match_score"] == 1.0


def test_preview_no_match_below_threshold(client, db_session):
    db_session.add(Ingredient(name="rec-olive-oil-99", unit="L", current_stock=1.0))
    db_session.flush()

    with patch("routers.recipe.parse_recipe_ingredients", return_value=[
        {
            "name": "xyzxyzxyz888abc",
            "quantity": 1.0,
            "unit": "ea",
            "quantity_display": "1 piece",
            "reasoning": "No idea.",
        }
    ]):
        resp = client.post("/api/recipe/preview", json={
            "name": "Test Recipe",
            "price": 10.0,
            "ingredient_text": "xyzxyzxyz888abc",
        })

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["suggested_match"] is None
    assert item["match_score"] == 0.0


def test_preview_no_db_writes(client, db_session):
    ing_count = db_session.query(Ingredient).count()
    recipe_count = db_session.query(Recipe).count()

    with patch("routers.recipe.parse_recipe_ingredients", return_value=PARSED_ITEMS):
        client.post("/api/recipe/preview", json={
            "name": "No Write Recipe",
            "price": 15.0,
            "ingredient_text": "salmon 200g, black pepper a pinch",
        })

    assert db_session.query(Ingredient).count() == ing_count
    assert db_session.query(Recipe).count() == recipe_count


def test_preview_empty_text_returns_400(client):
    resp = client.post("/api/recipe/preview", json={
        "name": "Test",
        "price": 10.0,
        "ingredient_text": "   ",
    })
    assert resp.status_code == 400


def test_preview_returns_recipe_meta(client):
    with patch("routers.recipe.parse_recipe_ingredients", return_value=PARSED_ITEMS):
        resp = client.post("/api/recipe/preview", json={
            "name": "rec-Meta Recipe-99",
            "description": "Some desc",
            "price": 22.5,
            "ingredient_text": "salmon 200g",
        })

    assert resp.status_code == 200
    body = resp.json()
    assert body["description"] == "Some desc"
    assert body["price"] == 22.5


# ── confirm ───────────────────────────────────────────────────────────────────

def test_confirm_links_existing_ingredient(client, db_session):
    ing = Ingredient(name="rec-cnf-salmon-99", unit="kg", current_stock=0.0)
    db_session.add(ing)
    db_session.flush()

    resp = client.post("/api/recipe/confirm", json={
        "name": "rec-Salmon Dish-99",
        "description": "Salmon dish",
        "price": 24.0,
        "items": [
            {
                "name": "rec-cnf-salmon-99",
                "quantity": 200.0,
                "unit": "g",
                "quantity_display": "200g",
                "ingredient_id": ing.id,
                "include": True,
            }
        ],
    })

    assert resp.status_code == 201
    body = resp.json()
    assert body["ingredients_linked"] == 1
    assert body["ingredients_created"] == 0

    recipe = db_session.query(Recipe).filter_by(name="rec-Salmon Dish-99").first()
    assert recipe is not None
    ri = db_session.query(RecipeIngredient).filter_by(recipe_id=recipe.id).first()
    assert ri is not None
    assert ri.quantity == 200.0


def test_confirm_creates_new_ingredient(client, db_session):
    resp = client.post("/api/recipe/confirm", json={
        "name": "rec-New Herb Dish-99",
        "price": 12.0,
        "items": [
            {
                "name": "rec-exotic-herb-99",
                "quantity": 5.0,
                "unit": "g",
                "quantity_display": "5g",
                "ingredient_id": None,
                "include": True,
            }
        ],
    })

    assert resp.status_code == 201
    body = resp.json()
    assert body["ingredients_created"] == 1
    assert body["ingredients_linked"] == 0

    new_ing = db_session.query(Ingredient).filter_by(name="rec-exotic-herb-99").first()
    assert new_ing is not None
    assert new_ing.current_stock == 0.0


def test_confirm_skips_excluded_items(client, db_session):
    resp = client.post("/api/recipe/confirm", json={
        "name": "rec-Skip Dish-99",
        "price": 8.0,
        "items": [
            {
                "name": "rec-excluded-99",
                "quantity": 1.0,
                "unit": "ea",
                "quantity_display": "1 piece",
                "ingredient_id": None,
                "include": False,
            }
        ],
    })

    assert resp.status_code == 201
    body = resp.json()
    assert body["ingredients_created"] == 0
    assert body["ingredients_linked"] == 0

    assert db_session.query(Ingredient).filter_by(name="rec-excluded-99").first() is None


def test_confirm_duplicate_name_returns_409(client, db_session):
    db_session.add(Recipe(name="rec-Duplicate-99", price=10.0))
    db_session.flush()

    resp = client.post("/api/recipe/confirm", json={
        "name": "rec-Duplicate-99",
        "price": 10.0,
        "items": [],
    })

    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_confirm_mixed_linked_and_created(client, db_session):
    ing = Ingredient(name="rec-mix-butter-99", unit="kg", current_stock=1.0)
    db_session.add(ing)
    db_session.flush()

    resp = client.post("/api/recipe/confirm", json={
        "name": "rec-Mixed Dish-99",
        "price": 18.0,
        "items": [
            {
                "name": "rec-mix-butter-99",
                "quantity": 50.0,
                "unit": "g",
                "quantity_display": "50g",
                "ingredient_id": ing.id,
                "include": True,
            },
            {
                "name": "rec-mix-new-spice-99",
                "quantity": 2.0,
                "unit": "g",
                "quantity_display": "a pinch",
                "ingredient_id": None,
                "include": True,
            },
            {
                "name": "rec-mix-skip-99",
                "quantity": 1.0,
                "unit": "ea",
                "quantity_display": "1",
                "ingredient_id": None,
                "include": False,
            },
        ],
    })

    assert resp.status_code == 201
    body = resp.json()
    assert body["ingredients_linked"] == 1
    assert body["ingredients_created"] == 1
