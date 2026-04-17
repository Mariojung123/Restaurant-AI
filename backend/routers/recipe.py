"""
Recipe endpoints.

Skeleton CRUD for recipes and their ingredient mappings. Sales logging
endpoints live here too so consumption data flows cleanly into the
prediction service.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    SalesLog,
    get_db,
)
from services.claude import parse_recipe_ingredients


router = APIRouter()


class RecipeIngredientIn(BaseModel):
    """Ingredient-to-recipe mapping payload."""

    ingredient_id: int
    quantity: Optional[float] = None
    unit: str = "unit"
    quantity_display: Optional[str] = None


class ParseRequest(BaseModel):
    """Natural language ingredient list to parse."""

    ingredient_text: str


class ParsedIngredient(BaseModel):
    """Single parsed ingredient returned before user confirmation."""

    name: str
    quantity: Optional[float]
    unit: str
    quantity_display: str
    reasoning: str


class RecipeIn(BaseModel):
    """Payload for creating a recipe."""

    name: str
    description: Optional[str] = None
    price: float = 0.0
    ingredients: list[RecipeIngredientIn] = Field(default_factory=list)


class RecipeOut(BaseModel):
    """Recipe representation returned by the API."""

    id: int
    name: str
    description: Optional[str]
    price: float

    class Config:
        from_attributes = True


class SalesLogIn(BaseModel):
    """Payload for recording a sale."""

    recipe_id: int
    quantity: int = 1
    total_price: Optional[float] = None


@router.post("/parse", response_model=list[ParsedIngredient])
def parse_recipe(payload: ParseRequest) -> list[ParsedIngredient]:
    """Parse a natural language ingredient list. Returns estimates + reasoning for user confirmation."""
    try:
        items = parse_recipe_ingredients(payload.ingredient_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude parsing failed: {e}")
    return [ParsedIngredient(**item) for item in items]


@router.get("/", response_model=list[RecipeOut])
def list_recipes(db: Session = Depends(get_db)) -> list[RecipeOut]:
    """Return every recipe on the menu."""
    return db.query(Recipe).order_by(Recipe.name).all()


@router.post("/", response_model=RecipeOut, status_code=201)
def create_recipe(payload: RecipeIn, db: Session = Depends(get_db)) -> RecipeOut:
    """Create a recipe and its ingredient mappings."""
    recipe = Recipe(
        name=payload.name,
        description=payload.description,
        price=payload.price,
    )
    db.add(recipe)
    db.flush()  # get recipe.id before linking ingredients

    for link in payload.ingredients:
        ingredient = db.query(Ingredient).filter(Ingredient.id == link.ingredient_id).first()
        if ingredient is None:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Ingredient not found: {link.ingredient_id}",
            )
        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=link.ingredient_id,
                quantity=link.quantity,
                unit=link.unit,
                quantity_display=link.quantity_display,
            )
        )

    db.commit()
    db.refresh(recipe)
    return recipe


@router.post("/sales", status_code=201)
def log_sale(payload: SalesLogIn, db: Session = Depends(get_db)) -> dict:
    """Record a sale of a recipe. Downstream consumers use this for forecasting."""
    recipe = db.query(Recipe).filter(Recipe.id == payload.recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    sale = SalesLog(
        recipe_id=payload.recipe_id,
        quantity=payload.quantity,
        total_price=payload.total_price,
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return {"id": sale.id, "sold_at": sale.sold_at.isoformat()}
