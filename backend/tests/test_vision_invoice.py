import json
from unittest.mock import patch

import pytest
from sqlalchemy import func

from models.database import Ingredient, InventoryLog
from services.invoice import process_invoice_items


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
    with patch("routers.vision.parse_image_with_claude", return_value=mock_resp):
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
    with patch("routers.vision.parse_image_with_claude", return_value=mock_resp):
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
    with patch("routers.vision.parse_image_with_claude", return_value=mock_resp):
        resp = _post_invoice(client)

    assert resp.status_code == 200
    assert resp.json()["items"][0]["action"] == "matched"

    count = db_session.query(Ingredient).filter(
        func.lower(Ingredient.name) == "olive oil"
    ).count()
    assert count == 1


def test_invoice_malformed_json_returns_422(client):
    with patch("routers.vision.parse_image_with_claude", return_value="not json"):
        resp = _post_invoice(client)
    assert resp.status_code == 422
    assert "non-JSON" in resp.json()["detail"]


def test_invoice_empty_items_returns_200(client):
    mock_resp = json.dumps({"supplier_name": "Unknown", "invoice_date": None, "items": []})
    with patch("routers.vision.parse_image_with_claude", return_value=mock_resp):
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
    with patch("routers.vision.parse_image_with_claude", return_value=raw_with_fences):
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
