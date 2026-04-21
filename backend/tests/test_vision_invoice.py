import json
from unittest.mock import patch

import pytest
from sqlalchemy import func

from models.database import Ingredient, InventoryLog
from services.invoice import fuzzy_match_ingredient, process_invoice_items


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_invoice_json(items, supplier="Test Supplier", date="2024-01-15"):
    return json.dumps({"supplier_name": supplier, "invoice_date": date, "items": items})


def _post_invoice(client, content=b"fake-image", content_type="image/jpeg"):
    return client.post(
        "/api/vision/invoice",
        files={"file": ("invoice.jpg", content, content_type)},
    )


# ── endpoint tests ────────────────────────────────────────────────────────────

def test_invoice_matches_existing_ingredient(client, db_session):
    db_session.add(Ingredient(name="chicken breast", unit="kg", current_stock=5.0))
    db_session.flush()

    mock_resp = _make_invoice_json(
        [{"name": "chicken breast", "quantity": 10.0, "unit": "kg",
          "unit_price": 8.5, "total_price": 85.0}]
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        resp = _post_invoice(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["supplier"] == "Test Supplier"
    assert body["invoice_date"] == "2024-01-15"
    assert body["items_processed"] == 1
    item = body["items"][0]
    assert item["action"] == "matched"
    assert item["quantity"] == 10.0

    ing = db_session.query(Ingredient).filter_by(name="chicken breast").first()
    assert ing.current_stock == 15.0


def test_invoice_creates_new_ingredient(client, db_session):
    mock_resp = _make_invoice_json(
        [{"name": "truffle oil", "quantity": 2.0, "unit": "L",
          "unit_price": 45.0, "total_price": 90.0}],
        supplier=None,
        date=None,
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        resp = _post_invoice(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["action"] == "created"

    ing = db_session.query(Ingredient).filter_by(name="truffle oil").first()
    assert ing is not None
    assert ing.current_stock == 2.0


def test_invoice_case_insensitive_match(client, db_session):
    db_session.add(Ingredient(name="Olive Oil", unit="L", current_stock=3.0))
    db_session.flush()

    mock_resp = _make_invoice_json(
        [{"name": "olive oil", "quantity": 1.0, "unit": "L",
          "unit_price": None, "total_price": None}]
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        resp = _post_invoice(client)

    assert resp.status_code == 200
    assert resp.json()["items"][0]["action"] == "matched"

    count = db_session.query(Ingredient).filter(
        func.lower(Ingredient.name) == "olive oil"
    ).count()
    assert count == 1


def test_invoice_malformed_json_returns_422(client):
    with patch("services.vision_common.parse_image_with_claude", return_value="not json"):
        resp = _post_invoice(client)
    assert resp.status_code == 422
    assert "non-JSON" in resp.json()["detail"]


def test_invoice_empty_items_returns_200(client):
    mock_resp = json.dumps({"supplier_name": "Unknown", "invoice_date": None, "items": []})
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        resp = _post_invoice(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["items_processed"] == 0
    assert body["items"] == []


def test_invoice_rejects_unsupported_type(client):
    resp = _post_invoice(client, content_type="application/pdf")
    assert resp.status_code == 400


def test_invoice_rejects_empty_file(client):
    resp = _post_invoice(client, content=b"")
    assert resp.status_code == 400


def test_invoice_strips_markdown_fences(client, db_session):
    inner = json.dumps({
        "supplier_name": "Fence Co",
        "invoice_date": "2024-03-01",
        "items": [{"name": "butter", "quantity": 5.0, "unit": "kg",
                   "unit_price": 3.0, "total_price": 15.0}],
    })
    raw_with_fences = f"```json\n{inner}\n```"
    with patch("services.vision_common.parse_image_with_claude", return_value=raw_with_fences):
        resp = _post_invoice(client)
    assert resp.status_code == 200
    assert resp.json()["supplier"] == "Fence Co"
    assert resp.json()["items"][0]["name"] == "butter"


# ── service unit test ─────────────────────────────────────────────────────────

def test_process_invoice_items_creates_log(db_session):
    items = [{"name": "salmon", "quantity": 3.0, "unit": "kg",
              "unit_price": 20.0, "total_price": 60.0}]
    results = process_invoice_items(items, "Sea Co", db_session)
    db_session.flush()

    assert len(results) == 1
    r = results[0]
    assert r["action"] == "created"
    assert r["quantity"] == 3.0

    log = db_session.query(InventoryLog).filter_by(ingredient_id=r["ingredient_id"]).first()
    assert log is not None
    assert log.change_type == "delivery"
    assert log.supplier == "Sea Co"
    assert log.quantity == 3.0


# ── preview endpoint tests ────────────────────────────────────────────────────

def _post_preview(client, content=b"fake-image", content_type="image/jpeg"):
    return client.post(
        "/api/vision/invoice/preview",
        files={"file": ("invoice.jpg", content, content_type)},
    )


def test_preview_returns_fuzzy_match(client, db_session):
    db_session.add(Ingredient(name="pvw-mozzarella-cheese-99", unit="kg", current_stock=2.0))
    db_session.flush()

    mock_resp = _make_invoice_json(
        [{"name": "pvw-mozz-cheese-99", "quantity": 3.0, "unit": "kg",
          "unit_price": None, "total_price": None}],
        supplier="PvwSupplierUnique99",
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        resp = _post_preview(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["duplicate_warning"] is False
    item = body["items"][0]
    assert item["suggested_match"] is not None
    assert item["suggested_match"]["name"] == "pvw-mozzarella-cheese-99"
    assert item["match_score"] >= 0.7


def test_preview_no_match_below_threshold(client, db_session):
    db_session.add(Ingredient(name="pvw-truffle-oil-99", unit="L", current_stock=1.0))
    db_session.flush()

    mock_resp = _make_invoice_json(
        [{"name": "xyzxyzxyz888abc", "quantity": 1.0, "unit": "ea",
          "unit_price": None, "total_price": None}],
        supplier="PvwNoMatchSupplier99",
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        resp = _post_preview(client)

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["suggested_match"] is None
    assert item["match_score"] == 0.0


def test_preview_no_db_writes(client, db_session):
    count_before = db_session.query(Ingredient).count()
    log_count_before = db_session.query(InventoryLog).count()

    mock_resp = _make_invoice_json(
        [{"name": "pvw-no-write-ingredient-99", "quantity": 5.0, "unit": "kg",
          "unit_price": 3.0, "total_price": 15.0}],
        supplier="PvwNoWriteSupplier99",
    )
    with patch("services.vision_common.parse_image_with_claude", return_value=mock_resp):
        _post_preview(client)

    assert db_session.query(Ingredient).count() == count_before
    assert db_session.query(InventoryLog).count() == log_count_before


def test_preview_rejects_unsupported_type(client):
    resp = _post_preview(client, content_type="application/pdf")
    assert resp.status_code == 400


# ── confirm endpoint tests ────────────────────────────────────────────────────

def test_confirm_saves_included_items(client, db_session):
    ing = Ingredient(name="cnf-chicken-breast-99", unit="kg", current_stock=5.0)
    db_session.add(ing)
    db_session.flush()

    payload = {
        "supplier": "CnfFarmCo99",
        "invoice_date": "2024-05-10",
        "items": [
            {
                "name": "cnf-chicken-breast-99",
                "quantity": 10.0,
                "unit": "kg",
                "unit_price": 5.99,
                "ingredient_id": ing.id,
                "include": True,
            },
            {
                "name": "cnf-unwanted-item-99",
                "quantity": 2.0,
                "unit": "ea",
                "unit_price": 1.0,
                "ingredient_id": None,
                "include": False,
            },
        ],
    }
    resp = client.post("/api/vision/invoice/confirm", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items_processed"] == 1
    assert body["items"][0]["action"] == "matched"

    db_session.expire_all()
    updated = db_session.query(Ingredient).filter_by(id=ing.id).first()
    assert updated.current_stock == 15.0

    excluded = db_session.query(Ingredient).filter_by(name="cnf-unwanted-item-99").first()
    assert excluded is None


def test_confirm_creates_new_ingredient_when_no_id(client, db_session):
    payload = {
        "supplier": "CnfHerbCo99",
        "invoice_date": "2024-05-11",
        "items": [
            {
                "name": "cnf-new-herb-mix-99",
                "quantity": 1.0,
                "unit": "bag",
                "unit_price": 4.50,
                "ingredient_id": None,
                "include": True,
            }
        ],
    }
    resp = client.post("/api/vision/invoice/confirm", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["action"] == "created"

    created = db_session.query(Ingredient).filter_by(name="cnf-new-herb-mix-99").first()
    assert created is not None
    assert created.current_stock == 1.0


def test_confirm_all_excluded_returns_zero(client, db_session):
    payload = {
        "supplier": "CnfNobody99",
        "invoice_date": "2024-05-12",
        "items": [
            {
                "name": "cnf-excluded-item-99",
                "quantity": 1.0,
                "unit": "ea",
                "unit_price": None,
                "ingredient_id": None,
                "include": False,
            }
        ],
    }
    resp = client.post("/api/vision/invoice/confirm", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items_processed"] == 0
    assert body["items"] == []


# ── unit conversion integration tests ────────────────────────────────────────

def test_process_invoice_items_cross_unit_g_to_kg(db_session):
    """Invoice delivers in g, ingredient stored in kg — stock must convert."""
    ing = Ingredient(name="uci-sugar-99", unit="kg", current_stock=1.0)
    db_session.add(ing)
    db_session.flush()

    items = [{"name": "uci-sugar-99", "quantity": 500.0, "unit": "g",
              "unit_price": None, "ingredient_id": ing.id}]
    results = process_invoice_items(items, "Supplier", db_session)
    db_session.flush()

    db_session.expire_all()
    updated = db_session.query(Ingredient).filter_by(id=ing.id).first()
    # 500g = 0.5kg added to 1.0kg → 1.5kg
    assert abs(updated.current_stock - 1.5) < 1e-6
    # log stores raw delivery quantity
    assert abs(results[0]["quantity"] - 500.0) < 1e-6


def test_process_invoice_items_cross_unit_ml_to_l(db_session):
    """Invoice delivers in mL, ingredient stored in L."""
    ing = Ingredient(name="uci-vinegar-99", unit="L", current_stock=0.5)
    db_session.add(ing)
    db_session.flush()

    items = [{"name": "uci-vinegar-99", "quantity": 750.0, "unit": "ml",
              "unit_price": None, "ingredient_id": ing.id}]
    results = process_invoice_items(items, "Supplier", db_session)
    db_session.flush()

    db_session.expire_all()
    updated = db_session.query(Ingredient).filter_by(id=ing.id).first()
    # 750mL = 0.75L added to 0.5L → 1.25L
    assert abs(updated.current_stock - 1.25) < 1e-6


# ── fuzzy match service unit test ─────────────────────────────────────────────

def test_fuzzy_match_ingredient_exact(db_session):
    db_session.add(Ingredient(name="fuz-chicken-breast-99", unit="kg", current_stock=0.0))
    db_session.flush()

    match, score = fuzzy_match_ingredient(db_session, "fuz-chicken-breast-99")
    assert match is not None
    assert score == 1.0


def test_fuzzy_match_ingredient_partial(db_session):
    db_session.add(Ingredient(name="fuz-mozzarella-cheese-99", unit="kg", current_stock=0.0))
    db_session.flush()

    match, score = fuzzy_match_ingredient(db_session, "fuz-mozz-cheese-99")
    assert match is not None
    assert score >= 0.7


def test_fuzzy_match_ingredient_no_match(db_session):
    db_session.add(Ingredient(name="fuz-olive-oil-99", unit="L", current_stock=0.0))
    db_session.flush()

    match, score = fuzzy_match_ingredient(db_session, "xyzxyzxyz999abc")
    assert match is None
    assert score == 0.0
