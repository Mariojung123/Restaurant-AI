import pytest

from services.unit_convert import convert_quantity


def test_same_unit_returns_unchanged():
    assert convert_quantity(5.0, "kg", "kg") == 5.0


def test_same_unit_case_insensitive():
    assert convert_quantity(5.0, "mL", "ml") == 5.0


def test_g_to_kg():
    assert abs(convert_quantity(500.0, "g", "kg") - 0.5) < 1e-9


def test_kg_to_g():
    assert abs(convert_quantity(2.0, "kg", "g") - 2000.0) < 1e-9


def test_ml_to_l():
    assert abs(convert_quantity(250.0, "ml", "l") - 0.25) < 1e-9


def test_l_to_ml():
    assert abs(convert_quantity(1.5, "l", "ml") - 1500.0) < 1e-9


def test_400g_from_30kg_stock():
    # core bug scenario: recipe uses 400g, ingredient stored in kg
    deduct = convert_quantity(400.0, "g", "kg")
    assert abs(deduct - 0.4) < 1e-9
    assert abs(30.0 - deduct - 29.6) < 1e-9


def test_unknown_from_unit_returns_zero(caplog):
    result = convert_quantity(5.0, "furlong", "kg")
    assert result == 0.0
    assert "Unknown unit" in caplog.text


def test_unknown_to_unit_returns_zero(caplog):
    result = convert_quantity(5.0, "kg", "parsec")
    assert result == 0.0
    assert "Unknown unit" in caplog.text


def test_incompatible_dimensions_returns_zero(caplog):
    result = convert_quantity(5.0, "kg", "l")
    assert result == 0.0
    assert "Incompatible" in caplog.text


def test_ea_to_ea():
    assert convert_quantity(3.0, "ea", "ea") == 3.0


def test_g_to_ea_returns_zero(caplog):
    result = convert_quantity(400.0, "g", "ea")
    assert result == 0.0
    assert "Incompatible" in caplog.text


def test_g_to_unit_returns_zero(caplog):
    result = convert_quantity(400.0, "g", "unit")
    assert result == 0.0
    assert "Incompatible" in caplog.text


def test_tsp_to_tbsp():
    assert abs(convert_quantity(3.0, "tsp", "tbsp") - 1.0) < 0.01


def test_cup_to_ml():
    assert abs(convert_quantity(1.0, "cup", "ml") - 240.0) < 1e-9
