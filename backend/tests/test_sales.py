"""Tests for GET /api/sales endpoint. Prefix: sal-"""

from datetime import datetime, timedelta, timezone

from models.database import Recipe, SalesLog


def _recipe(db, name, price=10.0):
    r = Recipe(name=name, price=price)
    db.add(r)
    db.flush()
    return r


def _sale(db, recipe_id, quantity=1, total_price=10.0, days_ago=0):
    sold_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    s = SalesLog(recipe_id=recipe_id, quantity=quantity, total_price=total_price, sold_at=sold_at)
    db.add(s)
    db.flush()
    return s


def test_sal_empty_db(client):
    resp = client.get("/api/sales")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_revenue"] == 0.0
    assert data["total_items_sold"] == 0
    assert data["daily_summaries"] == []
    assert data["menu_summaries"] == []


def test_sal_within_period(client, db_session):
    r = _recipe(db_session, "sal-Bibimbap")
    _sale(db_session, r.id, quantity=3, total_price=30.0, days_ago=1)
    _sale(db_session, r.id, quantity=2, total_price=20.0, days_ago=0)

    resp = client.get("/api/sales?period_days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items_sold"] == 5
    assert data["total_revenue"] == 50.0
    assert len(data["menu_summaries"]) == 1
    assert data["menu_summaries"][0]["recipe_name"] == "sal-Bibimbap"
    assert data["menu_summaries"][0]["quantity"] == 5
    assert len(data["daily_summaries"]) == 2


def test_sal_outside_period_excluded(client, db_session):
    r = _recipe(db_session, "sal-OldItem")
    _sale(db_session, r.id, quantity=5, total_price=50.0, days_ago=10)

    resp = client.get("/api/sales?period_days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items_sold"] == 0
    assert data["total_revenue"] == 0.0
    assert data["menu_summaries"] == []


def test_sal_null_total_price(client, db_session):
    r = _recipe(db_session, "sal-NullPrice")
    _sale(db_session, r.id, quantity=2, total_price=None, days_ago=0)

    resp = client.get("/api/sales?period_days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items_sold"] == 2
    assert data["total_revenue"] == 0.0
    assert data["menu_summaries"][0]["revenue"] == 0.0


def test_sal_period_days_1(client, db_session):
    r = _recipe(db_session, "sal-TodayItem")
    _sale(db_session, r.id, quantity=1, total_price=10.0, days_ago=0)
    _sale(db_session, r.id, quantity=1, total_price=10.0, days_ago=2)

    resp = client.get("/api/sales?period_days=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items_sold"] == 1
    assert data["total_revenue"] == 10.0


def test_sal_period_days_30(client, db_session):
    r = _recipe(db_session, "sal-MonthItem")
    _sale(db_session, r.id, quantity=10, total_price=100.0, days_ago=29)

    resp = client.get("/api/sales?period_days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items_sold"] == 10
    assert data["total_revenue"] == 100.0
