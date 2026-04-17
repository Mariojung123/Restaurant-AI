import os

# Set before any app imports so database.py reads correct URL
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-placeholder"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.database as db_module
import main as main_module
from models.database import Base, get_db
from main import app

# Thread-safe in-memory SQLite — StaticPool ensures all sessions share one connection
_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autoflush=False, autocommit=False, bind=_TEST_ENGINE)

# Patch module-level engine references so startup event and sessions both hit SQLite
db_module.engine = _TEST_ENGINE
db_module.SessionLocal = _TestSession
main_module.engine = _TEST_ENGINE

Base.metadata.create_all(bind=_TEST_ENGINE)


@pytest.fixture
def db_session():
    from sqlalchemy.orm import Session as SASession

    with _TEST_ENGINE.connect() as conn:
        conn.begin()
        session = SASession(conn, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        conn.rollback()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
