from datetime import datetime
from unittest.mock import patch

from models.database import Ingredient, Recipe, SalesLog
from routers.chat import _build_context


def test_chat_requires_session_id(client):
    resp = client.post(
        "/api/chat/message",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert resp.status_code == 422


def test_chat_saves_history(client, db_session):
    with patch("routers.chat.chat_with_claude", return_value="Test reply"):
        resp = client.post(
            "/api/chat/message",
            json={
                "session_id": "test-session-save",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "test-session-save"

    history = client.get("/api/chat/history/test-session-save").json()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "hello"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Test reply"


def test_chat_keyword_injects_inventory(db_session):
    db_session.add(Ingredient(name="chicken_breast", unit="kg", current_stock=5.0))
    db_session.flush()

    context = _build_context(db_session, "재고 얼마나 남았어?")

    assert "Inventory" in context
    assert "chicken_breast" in context


def test_chat_keyword_injects_sales(db_session):
    recipe = Recipe(name="Chicken_Salad", price=12.0)
    db_session.add(recipe)
    db_session.flush()

    db_session.add(SalesLog(recipe_id=recipe.id, quantity=5, sold_at=datetime.utcnow()))
    db_session.flush()

    context = _build_context(db_session, "판매 현황 보여줘")

    assert "Sales" in context
    assert "Chicken_Salad" in context


def test_chat_no_db_data_graceful(db_session):
    # No ingredients in DB — inventory keyword should produce empty context
    context = _build_context(db_session, "재고 얼마야?")
    assert context == ""
