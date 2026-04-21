"""Tests for recipe registration via chat (tool use flow)."""

from unittest.mock import MagicMock, patch

from models.database import Ingredient, Recipe, RecipeIngredient


def _text_message(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    msg.content = [block]
    return msg


def _tool_use_message(name: str, price: float, items: list[dict]) -> MagicMock:
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "tool_test_001"
    tool_block.name = "register_recipe"
    tool_block.input = {"name": name, "price": price, "items": items}
    msg = MagicMock()
    msg.stop_reason = "tool_use"
    msg.content = [tool_block]
    return msg


_AGLIO_ITEMS = [
    {"name": "pasta", "quantity": 120.0, "unit": "g", "quantity_display": "파스타 120g"},
    {"name": "garlic", "quantity": 9.0, "unit": "g", "quantity_display": "마늘 한 큰술"},
]


# ── tool use: recipe registration ────────────────────────────────────────────

def test_recipe_tool_use_saves_recipe(client, db_session):
    """Claude calls register_recipe → recipe appears in DB."""
    tool_msg = _tool_use_message("cr-Aglio Olio-01", 15.0, _AGLIO_ITEMS)
    final_msg = _text_message("Great! Aglio Olio has been registered.")

    with patch("routers.chat.chat_with_claude", side_effect=[tool_msg, final_msg]):
        resp = client.post("/api/chat/message", json={
            "session_id": "sess-cr-tool-01",
            "messages": [{"role": "user", "content": "yes, register it"}],
        })

    assert resp.status_code == 200
    assert "registered" in resp.json()["reply"].lower()

    recipe = db_session.query(Recipe).filter_by(name="cr-Aglio Olio-01").first()
    assert recipe is not None
    assert recipe.price == 15.0
    links = db_session.query(RecipeIngredient).filter_by(recipe_id=recipe.id).all()
    assert len(links) == 2


def test_recipe_tool_use_links_existing_ingredient(client, db_session):
    """Fuzzy match finds existing ingredient → linked, not duplicated."""
    ing = Ingredient(name="cr-pasta-02", unit="g", current_stock=500.0)
    db_session.add(ing)
    db_session.flush()

    items = [{"name": "cr-pasta-02", "quantity": 120.0, "unit": "g", "quantity_display": "120g"}]
    tool_msg = _tool_use_message("cr-Simple Pasta-02", 12.0, items)
    final_msg = _text_message("Done! cr-Simple Pasta-02 added.")

    with patch("routers.chat.chat_with_claude", side_effect=[tool_msg, final_msg]):
        resp = client.post("/api/chat/message", json={
            "session_id": "sess-cr-tool-02",
            "messages": [{"role": "user", "content": "yes"}],
        })

    assert resp.status_code == 200
    recipe = db_session.query(Recipe).filter_by(name="cr-Simple Pasta-02").first()
    assert recipe is not None
    link = db_session.query(RecipeIngredient).filter_by(recipe_id=recipe.id).first()
    assert link.ingredient_id == ing.id


def test_recipe_tool_duplicate_name_returns_error_in_reply(client, db_session):
    """Duplicate name → ValueError → tool_result error → Claude replies with error info."""
    db_session.add(Recipe(name="cr-Dup Recipe-03", price=0.0))
    db_session.flush()

    tool_msg = _tool_use_message("cr-Dup Recipe-03", 10.0, _AGLIO_ITEMS)
    final_msg = _text_message("That recipe already exists. Would you like a different name?")

    with patch("routers.chat.chat_with_claude", side_effect=[tool_msg, final_msg]):
        resp = client.post("/api/chat/message", json={
            "session_id": "sess-cr-dup-03",
            "messages": [{"role": "user", "content": "yes"}],
        })

    assert resp.status_code == 200
    recipe_count = db_session.query(Recipe).filter_by(name="cr-Dup Recipe-03").count()
    assert recipe_count == 1


def test_normal_chat_no_tool_call(client, db_session):
    """Non-registration message → text reply, no second Claude call, no recipe created."""
    text_msg = _text_message("Stock levels look healthy this week!")

    before = db_session.query(Recipe).count()
    with patch("routers.chat.chat_with_claude", return_value=text_msg) as mock_claude:
        resp = client.post("/api/chat/message", json={
            "session_id": "sess-cr-normal-04",
            "messages": [{"role": "user", "content": "how's inventory?"}],
        })

    assert resp.status_code == 200
    assert resp.json()["reply"] == "Stock levels look healthy this week!"
    assert mock_claude.call_count == 1
    assert db_session.query(Recipe).count() == before


def test_history_saved_after_tool_use(client, db_session):
    """After tool use, the final text reply (not tool internals) is saved to history."""
    tool_msg = _tool_use_message("cr-History Test-05", 8.0, _AGLIO_ITEMS)
    final_msg = _text_message("Registered! Anything else?")

    with patch("routers.chat.chat_with_claude", side_effect=[tool_msg, final_msg]):
        client.post("/api/chat/message", json={
            "session_id": "sess-cr-hist-05",
            "messages": [{"role": "user", "content": "yes"}],
        })

    history = client.get("/api/chat/history/sess-cr-hist-05").json()
    roles = [e["role"] for e in history]
    assert "user" in roles
    assert "assistant" in roles
    assert "pending_recipe" not in roles
    assistant_entry = next(e for e in history if e["role"] == "assistant")
    assert assistant_entry["content"] == "Registered! Anything else?"
