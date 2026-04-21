"""
Recipe endpoints.

CRUD for recipes and ingredient mappings. Two-step NL registration flow:
  POST /preview — parse + fuzzy match, no DB writes
  POST /confirm — save Recipe + RecipeIngredients
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import (
    Recipe,
    get_db,
)
from schemas.recipe import (
    ParseRequest,
    ParsedIngredient,
    RecipeIn,
    RecipeOut,
    SalesLogIn,
    RecipePreviewIn,
    SuggestedMatch,
    PreviewItem,
    RecipePreviewOut,
    RecipeConfirmIn,
    RecipeConfirmOut,
    RecipeDetailOut,
    RecipeUpdateIn,
)
from services.constants import DEFAULT_UNIT
from services.claude import parse_recipe_ingredients
from services.recipe_flow import build_preview_items, resolve_confirm_items
from services.recipe_svc import (
    create_recipe_with_links,
    delete_recipe_by_id,
    get_recipe_detail,
    record_recipe_sale,
    save_recipe_core,
    replace_recipe_ingredients,
    update_recipe_fields,
)


router = APIRouter()


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
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Claude returned invalid JSON: {e}")

    items = []
    for item in build_preview_items(db, parsed):
        suggested = item["suggested_match"]
        items.append(
            PreviewItem(
                name=item["name"],
                quantity=item["quantity"],
                unit=item.get("unit", DEFAULT_UNIT),
                quantity_display=item["quantity_display"],
                reasoning=item["reasoning"],
                suggested_match=SuggestedMatch(**suggested) if suggested else None,
                match_score=item["match_score"],
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
    try:
        resolved = resolve_confirm_items(db, payload.items)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

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
    except (ValueError, RuntimeError, json.JSONDecodeError) as e:
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
    try:
        recipe = create_recipe_with_links(
            db,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            ingredients=payload.ingredients,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    db.commit()
    db.refresh(recipe)
    return recipe


@router.post("/sales", status_code=201)
def log_sale(payload: SalesLogIn, db: Session = Depends(get_db)) -> dict:
    """Record a sale of a recipe."""
    try:
        sale = record_recipe_sale(
            db,
            recipe_id=payload.recipe_id,
            quantity=payload.quantity,
            total_price=payload.total_price,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    db.commit()
    db.refresh(sale)
    return {"id": sale.id, "sold_at": sale.sold_at.isoformat()}
