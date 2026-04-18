# PRP: Recipe Natural Language Registration

## Goal
3-step UI + 2-step API for creating recipes via natural language ingredient input.

## Endpoints
- `POST /api/recipe/preview` — parse NL ingredients via Claude + fuzzy match against Ingredient table, no DB writes
- `POST /api/recipe/confirm` — save Recipe + RecipeIngredients, create new Ingredients where needed

## Reused
- `parse_recipe_ingredients()` — services/claude.py
- `fuzzy_match_ingredient()` — services/invoice.py
- `_create_ingredient()` — services/invoice.py
- Invoice.jsx step pattern — UI

## Files Changed
| File | Change |
|------|--------|
| `backend/routers/recipe.py` | Add `/preview`, `/confirm` endpoints |
| `frontend/src/pages/Recipe.jsx` | Add 3-step registration flow |
| `backend/tests/test_recipe_register.py` | New test file |

## Key Rules
- preview: no DB writes
- confirm: 409 on duplicate recipe name (case-insensitive)
- `include: false` items skipped in confirm
- `ingredient_id: null + include: true` → new Ingredient created (current_stock=0)
- Unit mismatch allowed: store as-is, no conversion
- `quantity_display` preserved verbatim
