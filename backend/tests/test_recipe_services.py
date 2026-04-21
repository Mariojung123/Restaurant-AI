from schemas.recipe import ConfirmItem, RecipeIngredientIn
from services.recipe_flow import resolve_confirm_items
from services.recipe_svc import create_recipe_with_links, record_recipe_sale
from models.database import Ingredient, RecipeIngredient, SalesLog


def test_rsv_create_recipe_with_links_creates_rows(db_session):
    ing = Ingredient(name="rsv-link-ing-01", unit="g", current_stock=0.0)
    db_session.add(ing)
    db_session.flush()

    recipe = create_recipe_with_links(
        db_session,
        name="rsv-link-recipe-01",
        description="service create test",
        price=9.5,
        ingredients=[RecipeIngredientIn(ingredient_id=ing.id, quantity=12.0, unit="g")],
    )

    link = (
        db_session.query(RecipeIngredient)
        .filter(RecipeIngredient.recipe_id == recipe.id, RecipeIngredient.ingredient_id == ing.id)
        .first()
    )
    assert recipe.id is not None
    assert link is not None
    assert link.quantity == 12.0


def test_rsv_create_recipe_with_links_raises_for_missing_ingredient(db_session):
    try:
        create_recipe_with_links(
            db_session,
            name="rsv-missing-ing-recipe-01",
            description=None,
            price=5.0,
            ingredients=[RecipeIngredientIn(ingredient_id=999999, quantity=1.0, unit="ea")],
        )
        assert False, "Expected ValueError for missing ingredient"
    except ValueError as exc:
        assert "Ingredient not found" in str(exc)


def test_rsv_record_recipe_sale_persists_sales_log(db_session):
    recipe = create_recipe_with_links(
        db_session,
        name="rsv-sale-recipe-01",
        description=None,
        price=14.0,
        ingredients=[],
    )
    sale = record_recipe_sale(db_session, recipe.id, quantity=3, total_price=42.0)

    saved = db_session.query(SalesLog).filter(SalesLog.id == sale.id).first()
    assert saved is not None
    assert saved.quantity == 3
    assert saved.total_price == 42.0


def test_rsv_resolve_confirm_items_filters_and_resolves(db_session):
    ing = Ingredient(name="rsv-confirm-ing-01", unit="g", current_stock=0.0)
    db_session.add(ing)
    db_session.flush()

    items = [
        ConfirmItem(
            name="rsv-confirm-ing-01",
            quantity=5.0,
            unit="g",
            ingredient_id=ing.id,
            include=True,
        ),
        ConfirmItem(
            name="rsv-confirm-skip-01",
            quantity=1.0,
            unit="ea",
            include=False,
        ),
    ]

    resolved = resolve_confirm_items(db_session, items)
    assert len(resolved) == 1
    assert resolved[0]["ingredient"].id == ing.id
    assert resolved[0]["name"] == "rsv-confirm-ing-01"
