"""Tests for recipe registration via chat (pending flow)."""

import json
from unittest.mock import patch

import pytest

from models.database import ChatHistory, Ingredient, Recipe, RecipeIngredient
from routers.chat import (
    _is_confirmation,
    _is_recipe_register_intent,
    _is_rejection,
)
from services.pending_recipe import (
    format_confirmation_message as _format_confirmation_message,
    get_pending as _get_pending_recipe,
    save_pending as _save_pending_recipe,
)


PARSED_AGLIO = {
    "name": "알리오 올리오",
    "items": [
        {
            "name": "pasta",
            "quantity": 120.0,
            "unit": "g",
            "quantity_display": "파스타 120g",
            "reasoning": None,
        },
        {
            "name": "garlic",
            "quantity": 9.0,
            "unit": "g",
            "quantity_display": "마늘 한 큰술",
            "reasoning": "마늘 한 큰술은 약 9g 정도 입니다!",
        },
        {
            "name": "salt",
            "quantity": 2.0,
            "unit": "g",
            "quantity_display": "소금 조금",
            "reasoning": "소금 조금은 약 2g 정도 입니다!",
        },
    ],
}


# ── unit: keyword detection ───────────────────────────────────────────────────

def test_is_recipe_register_intent_korean():
    assert _is_recipe_register_intent("알리오 올리오 레시피 등록해줘")
    assert _is_recipe_register_intent("새 레시피 추가해줘, 재료는...")
    assert _is_recipe_register_intent("레시피를 등록하고 싶어")

def test_is_recipe_register_intent_english():
    assert _is_recipe_register_intent("add recipe: pasta 120g")
    assert _is_recipe_register_intent("register recipe aglio olio")

def test_is_recipe_register_intent_negative():
    assert not _is_recipe_register_intent("재고 얼마나 남았어?")
    assert not _is_recipe_register_intent("이번 주 뭐가 잘 팔렸어?")

def test_is_confirmation():
    assert _is_confirmation("응")
    assert _is_confirmation("네")
    assert _is_confirmation("좋아")
    assert _is_confirmation("ok")
    assert _is_confirmation("yes")
    assert not _is_confirmation("아니")
    assert not _is_confirmation("취소")

def test_is_rejection():
    assert _is_rejection("아니")
    assert _is_rejection("취소할게")
    assert _is_rejection("하지마")
    assert not _is_rejection("응")
    assert not _is_rejection("네")


# ── unit: format confirmation message ────────────────────────────────────────

def test_format_confirmation_message_structure():
    msg = _format_confirmation_message(PARSED_AGLIO)
    assert "알리오 올리오" in msg
    assert "pasta" in msg
    assert "마늘 한 큰술은 약 9g" in msg
    assert "소금 조금은 약 2g" in msg
    assert "네 / 아니오" in msg

def test_format_confirmation_message_no_reasoning():
    parsed = {
        "name": "Test",
        "items": [
            {"name": "pasta", "quantity": 100.0, "unit": "g",
             "quantity_display": "100g", "reasoning": None}
        ],
    }
    msg = _format_confirmation_message(parsed)
    assert "pasta" in msg
    # ingredient line should have no reasoning parentheses
    ingredient_line = [l for l in msg.split("\n") if "pasta" in l][0]
    assert "(" not in ingredient_line


# ── unit: pending recipe helpers ──────────────────────────────────────────────

def test_save_and_get_pending_recipe(db_session):
    _save_pending_recipe(db_session, "sess-cr-001", PARSED_AGLIO)
    result = _get_pending_recipe(db_session, "sess-cr-001")
    assert result is not None
    assert result["name"] == "알리오 올리오"
    assert len(result["items"]) == 3

def test_save_pending_clears_previous(db_session):
    _save_pending_recipe(db_session, "sess-cr-002", PARSED_AGLIO)
    new_data = {**PARSED_AGLIO, "name": "Updated"}
    _save_pending_recipe(db_session, "sess-cr-002", new_data)

    count = (
        db_session.query(ChatHistory)
        .filter_by(session_id="sess-cr-002", role="pending_recipe")
        .count()
    )
    assert count == 1
    assert _get_pending_recipe(db_session, "sess-cr-002")["name"] == "Updated"

def test_get_pending_returns_none_when_empty(db_session):
    assert _get_pending_recipe(db_session, "sess-cr-no-pending") is None


# ── endpoint: full registration flow ─────────────────────────────────────────

def test_chat_recipe_register_creates_pending(client, db_session):
    with patch("routers.chat.extract_recipe_from_chat", return_value=PARSED_AGLIO):
        resp = client.post("/api/chat/message", json={
            "session_id": "sess-cr-reg-01",
            "messages": [{"role": "user", "content": "알리오 올리오 레시피 등록해줘"}],
        })

    assert resp.status_code == 200
    reply = resp.json()["reply"]
    assert "알리오 올리오" in reply
    assert "마늘 한 큰술은 약 9g" in reply
    assert "네 / 아니오" in reply

    pending = _get_pending_recipe(db_session, "sess-cr-reg-01")
    assert pending is not None
    assert pending["name"] == "알리오 올리오"


def test_chat_recipe_confirm_saves_recipe(client, db_session):
    ing = Ingredient(name="cr-garlic-99", unit="g", current_stock=100.0)
    db_session.add(ing)
    db_session.flush()

    parsed = {
        "name": "cr-Aglio Olio-99",
        "items": [
            {"name": "cr-garlic-99", "quantity": 9.0, "unit": "g",
             "quantity_display": "한 큰술", "reasoning": "약 9g"},
            {"name": "cr-new-pasta-99", "quantity": 120.0, "unit": "g",
             "quantity_display": "120g", "reasoning": None},
        ],
    }
    _save_pending_recipe(db_session, "sess-cr-cnf-01", parsed)

    resp = client.post("/api/chat/message", json={
        "session_id": "sess-cr-cnf-01",
        "messages": [{"role": "user", "content": "응"}],
    })

    assert resp.status_code == 200
    reply = resp.json()["reply"]
    assert "등록 완료" in reply

    recipe = db_session.query(Recipe).filter_by(name="cr-Aglio Olio-99").first()
    assert recipe is not None
    links = db_session.query(RecipeIngredient).filter_by(recipe_id=recipe.id).all()
    assert len(links) == 2

    assert _get_pending_recipe(db_session, "sess-cr-cnf-01") is None


def test_chat_recipe_reject_clears_pending(client, db_session):
    _save_pending_recipe(db_session, "sess-cr-rej-01", PARSED_AGLIO)

    resp = client.post("/api/chat/message", json={
        "session_id": "sess-cr-rej-01",
        "messages": [{"role": "user", "content": "아니"}],
    })

    assert resp.status_code == 200
    assert "취소" in resp.json()["reply"]
    assert _get_pending_recipe(db_session, "sess-cr-rej-01") is None


def test_chat_recipe_duplicate_name_returns_warning(client, db_session):
    db_session.add(Recipe(name="cr-Dup Recipe-99", price=0.0))
    db_session.flush()

    parsed = {**PARSED_AGLIO, "name": "cr-Dup Recipe-99"}
    _save_pending_recipe(db_session, "sess-cr-dup-01", parsed)

    resp = client.post("/api/chat/message", json={
        "session_id": "sess-cr-dup-01",
        "messages": [{"role": "user", "content": "네"}],
    })

    assert resp.status_code == 200
    assert "cr-Dup Recipe-99" in resp.json()["reply"]


def test_chat_recipe_history_excludes_pending(client, db_session):
    _save_pending_recipe(db_session, "sess-cr-hist-01", PARSED_AGLIO)

    resp = client.get("/api/chat/history/sess-cr-hist-01")
    assert resp.status_code == 200
    roles = [entry["role"] for entry in resp.json()]
    assert "pending_recipe" not in roles


def test_chat_recipe_register_fallthrough_on_parse_error(client, db_session):
    with patch("routers.chat.extract_recipe_from_chat", side_effect=ValueError("Claude error")):
        with patch("routers.chat.chat_with_claude", return_value="Claude normal reply"):
            resp = client.post("/api/chat/message", json={
                "session_id": "sess-cr-fallback-01",
                "messages": [{"role": "user", "content": "레시피 등록해줘"}],
            })

    assert resp.status_code == 200
    assert resp.json()["reply"] == "Claude normal reply"
    assert _get_pending_recipe(db_session, "sess-cr-fallback-01") is None
