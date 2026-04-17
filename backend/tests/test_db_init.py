from sqlalchemy import inspect, text
from tests.conftest import _TEST_ENGINE


EXPECTED_TABLES = {
    "ingredients",
    "recipes",
    "recipe_ingredients",
    "inventory_logs",
    "sales_logs",
    "chat_history",
}


def test_db_tables_created():
    inspector = inspect(_TEST_ENGINE)
    actual = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(actual), f"Missing tables: {EXPECTED_TABLES - actual}"


def test_db_connection():
    with _TEST_ENGINE.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    assert result == 1
