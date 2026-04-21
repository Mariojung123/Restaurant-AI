"""
SQLAlchemy models and database connection for Restaurant AI Partner.

Tables:
- ingredients: raw materials used in recipes
- recipes: menu items
- recipe_ingredients: many-to-many link with quantity per recipe
- inventory_logs: stock in/out events (purchases, deliveries, adjustments)
- sales_logs: per-item sales events used for consumption prediction
"""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    create_engine,
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/restaurant_ai",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Ingredient(Base):
    """A raw ingredient tracked in inventory."""

    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    unit = Column(String(32), nullable=False, default="unit")  # kg, L, ea, etc.
    current_stock = Column(Float, nullable=False, default=0.0)
    reorder_threshold = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    recipe_links = relationship(
        "RecipeIngredient",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )
    inventory_logs = relationship(
        "InventoryLog",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )


class Recipe(Base):
    """A menu item that consumes ingredients when sold."""

    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    ingredient_links = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )
    sales_logs = relationship(
        "SalesLog",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )


class RecipeIngredient(Base):
    """Join table mapping a recipe to its ingredients and per-serving quantities."""

    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False
    )
    quantity = Column(Float, nullable=True)  # null = vague amount ("조금", "약간")
    unit = Column(String(32), nullable=False, default="unit")
    quantity_display = Column(Text, nullable=True)  # original natural language ("한 웅큼")

    recipe = relationship("Recipe", back_populates="ingredient_links")
    ingredient = relationship("Ingredient", back_populates="recipe_links")


class InventoryLog(Base):
    """Record of stock changes: deliveries, purchases, or manual adjustments."""

    __tablename__ = "inventory_logs"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False
    )
    change_type = Column(String(32), nullable=False)  # purchase, delivery, adjustment
    quantity = Column(Float, nullable=False)  # positive for in, negative for out
    unit_cost = Column(Float, nullable=True)
    supplier = Column(String(200), nullable=True)
    note = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=utc_now, nullable=False)

    ingredient = relationship("Ingredient", back_populates="inventory_logs")


class SalesLog(Base):
    """Record of a recipe being sold; used for consumption pattern analysis."""

    __tablename__ = "sales_logs"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    total_price = Column(Float, nullable=True)
    sold_at = Column(DateTime, default=utc_now, nullable=False)

    recipe = relationship("Recipe", back_populates="sales_logs")


class ChatHistory(Base):
    """Multi-turn conversation history for context-aware Claude responses."""

    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
