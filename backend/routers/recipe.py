"""
Recipe endpoints.

CRUD for recipes and ingredient mappings. Two-step NL registration flow:
  POST /preview — parse + fuzzy match, no DB writes
  POST /confirm — save Recipe + RecipeIngredients
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
from services.ingredient import create_ingredient, fuzzy_match_ingredient
from services.recipe_svc import (
    delete_recipe_by_id,
    get_recipe_detail,
    save_recipe_core,
    replace_recipe_ingredients,
    update_recipe_fields,
)


router = APIRouter()


# ── models ────────────────────────────────────────────────────────────────────

class RecipeIngredientIn(BaseModel):
    ingredient_id: int
    quantity: Optional[float] = None
    unit: str = "unit"
    quantity_display: Optional[str] = None


class ParseRequest(BaseModel):
    ingredient_text: str


class ParsedIngredient(BaseModel):
    name: str
    quantity: Optional[float]
    unit: str
    quantity_display: str
    reasoning: str


class RecipeIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    ingredients: list[RecipeIngredientIn] = Field(default_factory=list)


class RecipeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float

    class Config:
        from_attributes = True


class SalesLogIn(BaseModel):
    recipe_id: int
    quantity: int = 1
    total_price: Optional[float] = None


class RecipePreviewIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    ingredient_text: str


class SuggestedMatch(BaseModel):
    id: int
    name: str
    unit: str


class PreviewItem(BaseModel):
    name: str
    quantity: Optional[float]
    unit: str
    quantity_display: str
    reasoning: str
    suggested_match: Optional[SuggestedMatch]
    match_score: float


class RecipePreviewOut(BaseModel):
    name: str
    description: Optional[str]
    price: float
    items: list[PreviewItem]


class ConfirmItem(BaseModel):
    name: str
    quantity: Optional[float] = None
    unit: str = "unit"
    quantity_display: str = ""
    ingredient_id: Optional[int] = None
    include: bool = True


class RecipeConfirmIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    items: list[ConfirmItem] = Field(default_factory=list)


class RecipeConfirmOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    ingredients_linked: int
    ingredients_created: int


class IngredientDetail(BaseModel):
    link_id: int
    ingredient_id: int
    name: str
    quantity: Optional[float]
    unit: str
    quantity_display: Optional[str]


class RecipeDetailOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    ingredients: list[IngredientDetail]

    class Config:
        from_attributes = True


class RecipeUpdateIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    items: Optional[list[ConfirmItem]] = None


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/preview", response_model=RecipePreviewOut)
def preview_recipe(payload: RecipePreviewIn, db: Session = Depends(get_db)):
    """Parse NL ingredients + fuzzy match against existing Ingredients. No DB writes."""
    if not payload.ingredient_text.strip():
        raise HTTPException(status_code=400, detail="ingredient_text is required")

    try:
        parsed = parse_recipe_ingredients(payload.ingredient_text)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"Claude parsing failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {e}")

    items = []
    for item in parsed:
        match, score = fuzzy_match_ingredient(db, item["name"])
        suggested = None
        if match:
            suggested = SuggestedMatch(id=match.id, name=match.name, unit=match.unit)
        items.append(
            PreviewItem(
                name=item["name"],
                quantity=item.get("quantity"),
                unit=item.get("unit", "unit"),
                quantity_display=item.get("quantity_display", ""),
                reasoning=item.get("reasoning", ""),
                suggested_match=suggested,
                match_score=score,
            )
        )

    return RecipePreviewOut(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        items=items,
    )


@router.post("/confirm", response_model=RecipeConfirmOut, status_code=201)
def confirm_recipe(payload: RecipeConfirmIn, db: Session = Depends(get_db)):
    """Save Recipe + RecipeIngredients. Creates new Ingredients where ingredient_id is null."""
    resolved = []
    for item in payload.items:
        if not item.include:
            continue
        ingredient = None
        if item.ingredient_id is not None:
            ingredient = db.query(Ingredient).filter(Ingredient.id == item.ingredient_id).first()
            if ingredient is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Ingredient not found: {item.ingredient_id}",
                )
        resolved.append({
            "ingredient": ingredient,
            "name": item.name,
            "quantity": item.quantity,
            "unit": item.unit,
            "quantity_display": item.quantity_display or None,
        })

    try:
        result = save_recipe_core(
            db,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            resolved_items=resolved,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    db.commit()
    recipe = db.query(Recipe).filter(Recipe.id == result["id"]).first()

    return RecipeConfirmOut(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        price=recipe.price,
        ingredients_linked=result["ingredients_linked"],
        ingredients_created=result["ingredients_created"],
    )


@router.post("/parse", response_model=list[ParsedIngredient])
def parse_recipe(payload: ParseRequest) -> list[ParsedIngredient]:
    """Parse a natural language ingredient list. Returns estimates + reasoning for confirmation."""
    try:
        items = parse_recipe_ingredients(payload.ingredient_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude parsing failed: {e}")
    return [ParsedIngredient(**item) for item in items]


@router.get("/", response_model=list[RecipeOut])
def list_recipes(db: Session = Depends(get_db)) -> list[RecipeOut]:
    return db.query(Recipe).order_by(Recipe.name).all()


@router.get("/{recipe_id}", response_model=RecipeDetailOut)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)) -> RecipeDetailOut:
    detail = get_recipe_detail(db, recipe_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RecipeDetailOut(**detail)


@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(recipe_id: int, payload: RecipeUpdateIn, db: Session = Depends(get_db)) -> RecipeOut:
    try:
        recipe = update_recipe_fields(db, recipe_id, payload.name, payload.description, payload.price)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if payload.items is not None:
            replace_recipe_ingredients(db, recipe_id, [i.model_dump() for i in payload.items])
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)) -> None:
    if not delete_recipe_by_id(db, recipe_id):
        raise HTTPException(status_code=404, detail="Recipe not found")
    db.commit()


@router.post("/", response_model=RecipeOut, status_code=201)
def create_recipe(payload: RecipeIn, db: Session = Depends(get_db)) -> RecipeOut:
    """Create a recipe and its ingredient mappings."""
    recipe = Recipe(
        name=payload.name,
        description=payload.description,
        price=payload.price,
    )
    db.add(recipe)
    db.flush()

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
    """Record a sale of a recipe."""
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
