import { useEffect, useReducer } from 'react';
import { listRecipes, getRecipe, confirmRecipe, updateRecipe, deleteRecipe } from '../api/recipe.js';
import { listIngredients } from '../api/inventory.js';

const STEP = { LIST: 'list', INPUT: 'input', DONE: 'done', DETAIL: 'detail', EDIT: 'edit' };
const UNITS = ['g', 'ml', 'ea', 'tsp', 'tbsp', 'oz', 'cup', 'kg', 'L'];
const EMPTY_FORM = { name: '', price: '', description: '' };
const emptyRow = () => ({ ingredientId: '', quantity: '', unit: 'g' });

const initialState = {
  step: STEP.LIST,
  recipes: [],
  listStatus: 'loading',
  listError: null,
  selectedRecipe: null,
  detailStatus: 'idle',
  deleteConfirm: false,
  form: EMPTY_FORM,
  ingredientRows: [emptyRow()],
  ingredients: [],
  loading: false,
  error: '',
  result: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'LIST_LOADING':
      return { ...state, listStatus: 'loading' };
    case 'LIST_SUCCESS':
      return { ...state, listStatus: 'ready', recipes: action.recipes };
    case 'LIST_ERROR':
      return { ...state, listStatus: 'error', listError: action.error };
    case 'GO_TO_INPUT':
      return { ...state, step: STEP.INPUT, error: '', form: EMPTY_FORM, ingredientRows: [emptyRow()] };
    case 'GO_TO_LIST':
      return { ...state, step: STEP.LIST, deleteConfirm: false };
    case 'GO_TO_DETAIL':
      return { ...state, step: STEP.DETAIL, selectedRecipe: action.recipe, detailStatus: 'ready', deleteConfirm: false, error: '' };
    case 'DETAIL_LOADING':
      return { ...state, detailStatus: 'loading' };
    case 'GO_TO_EDIT':
      return {
        ...state,
        step: STEP.EDIT,
        form: {
          name: state.selectedRecipe.name,
          price: String(state.selectedRecipe.price),
          description: state.selectedRecipe.description ?? '',
        },
        ingredientRows: state.selectedRecipe.ingredients.map((ing) => ({
          ingredientId: String(ing.ingredient_id),
          quantity: ing.quantity != null ? String(ing.quantity) : '',
          unit: ing.unit,
        })),
        error: '',
      };
    case 'SET_DELETE_CONFIRM':
      return { ...state, deleteConfirm: action.value };
    case 'FORM_UPDATE':
      return { ...state, form: { ...state.form, [action.field]: action.value } };
    case 'INGREDIENTS_LOADED':
      return { ...state, ingredients: action.ingredients };
    case 'ADD_ROW':
      return { ...state, ingredientRows: [...state.ingredientRows, emptyRow()] };
    case 'REMOVE_ROW':
      return { ...state, ingredientRows: state.ingredientRows.filter((_, i) => i !== action.idx) };
    case 'UPDATE_ROW': {
      const rows = state.ingredientRows.map((r, i) => {
        if (i !== action.idx) return r;
        const updated = { ...r, [action.field]: action.value };
        if (action.field === 'ingredientId' && action.autoUnit) {
          updated.unit = action.autoUnit;
        }
        return updated;
      });
      return { ...state, ingredientRows: rows };
    }
    case 'SAVE_START':
      return { ...state, loading: true, error: '' };
    case 'SAVE_SUCCESS':
      return { ...state, loading: false, step: STEP.DONE, result: action.result };
    case 'REQUEST_ERROR':
      return { ...state, loading: false, error: action.error };
    case 'RESET_FLOW':
      return { ...state, step: STEP.INPUT, form: EMPTY_FORM, ingredientRows: [emptyRow()], result: null, error: '' };
    default:
      return state;
  }
}

function Recipe() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const {
    step, recipes, listStatus, listError,
    selectedRecipe, detailStatus, deleteConfirm,
    form, ingredientRows, ingredients, loading, error, result,
  } = state;

  useEffect(() => {
    if (step !== STEP.LIST) return;
    let cancelled = false;
    dispatch({ type: 'LIST_LOADING' });
    listRecipes()
      .then((data) => { if (!cancelled) dispatch({ type: 'LIST_SUCCESS', recipes: data }); })
      .catch((e) => { if (!cancelled) dispatch({ type: 'LIST_ERROR', error: e.message }); });
    return () => { cancelled = true; };
  }, [step]);

  useEffect(() => {
    if ((step !== STEP.INPUT && step !== STEP.EDIT) || ingredients.length > 0) return;
    listIngredients()
      .then((data) => dispatch({ type: 'INGREDIENTS_LOADED', ingredients: data }))
      .catch(() => {});
  }, [step, ingredients.length]);

  async function handleSelectRecipe(recipeId) {
    dispatch({ type: 'DETAIL_LOADING' });
    try {
      const data = await getRecipe(recipeId);
      dispatch({ type: 'GO_TO_DETAIL', recipe: data });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleUpdate() {
    dispatch({ type: 'SAVE_START' });
    try {
      const items = buildItems(ingredientRows);
      const updated = await updateRecipe(selectedRecipe.id, {
        name: form.name.trim(),
        description: form.description.trim() || null,
        price: parseFloat(form.price) || 0,
        items,
      });
      const detail = await getRecipe(selectedRecipe.id);
      dispatch({ type: 'GO_TO_DETAIL', recipe: detail });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleDelete() {
    dispatch({ type: 'SAVE_START' });
    try {
      await deleteRecipe(selectedRecipe.id);
      dispatch({ type: 'GO_TO_LIST' });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleSave() {
    const items = buildItems(ingredientRows);
    if (items.length === 0) {
      dispatch({ type: 'REQUEST_ERROR', error: 'Add at least one ingredient with a quantity.' });
      return;
    }
    dispatch({ type: 'SAVE_START' });
    try {
      const data = await confirmRecipe({
        name: form.name.trim(),
        description: form.description.trim() || null,
        price: parseFloat(form.price) || 0,
        items,
      });
      dispatch({ type: 'SAVE_SUCCESS', result: data });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  function handleRowIngredientChange(idx, ingredientId) {
    const ing = ingredients.find((i) => i.id === parseInt(ingredientId, 10));
    dispatch({ type: 'UPDATE_ROW', idx, field: 'ingredientId', value: ingredientId, autoUnit: ing?.unit });
  }

  function buildItems(rows) {
    return rows
      .filter((r) => r.ingredientId && r.quantity)
      .map((r) => {
        const ing = ingredients.find((i) => i.id === parseInt(r.ingredientId, 10));
        return {
          name: ing.name,
          quantity: parseFloat(r.quantity),
          unit: r.unit,
          quantity_display: `${r.quantity}${r.unit}`,
          ingredient_id: ing.id,
          include: true,
        };
      });
  }

  function renderIngredientRows() {
    const usedIds = new Set(ingredientRows.map((r) => r.ingredientId).filter(Boolean));
    return (
      <>
        {ingredientRows.map((row, idx) => (
          <div key={idx} className="flex gap-2 items-center">
            <select
              className="flex-1 border rounded px-2 py-1.5 text-sm text-slate-700 bg-white"
              value={row.ingredientId}
              onChange={(e) => handleRowIngredientChange(idx, e.target.value)}
            >
              <option value="">Select ingredient…</option>
              {ingredients.map((ing) => (
                <option
                  key={ing.id}
                  value={ing.id}
                  disabled={usedIds.has(String(ing.id)) && row.ingredientId !== String(ing.id)}
                >
                  {ing.name}
                </option>
              ))}
            </select>
            <input
              className="w-20 border rounded px-2 py-1.5 text-sm"
              type="number" min="0" step="any" placeholder="Qty"
              value={row.quantity}
              onChange={(e) => dispatch({ type: 'UPDATE_ROW', idx, field: 'quantity', value: e.target.value })}
            />
            <select
              className="w-20 border rounded px-2 py-1.5 text-sm bg-white"
              value={row.unit}
              onChange={(e) => dispatch({ type: 'UPDATE_ROW', idx, field: 'unit', value: e.target.value })}
            >
              {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
            <button
              onClick={() => dispatch({ type: 'REMOVE_ROW', idx })}
              disabled={ingredientRows.length === 1}
              className="text-slate-400 hover:text-red-500 disabled:opacity-20 text-lg leading-none px-1"
            >
              ✕
            </button>
          </div>
        ))}
        <button
          onClick={() => dispatch({ type: 'ADD_ROW' })}
          className="self-start text-sm text-brand hover:underline mt-1"
        >
          + Add Ingredient
        </button>
      </>
    );
  }

  // ── DETAIL ───────────────────────────────────────────────────────────────────
  if (step === STEP.DETAIL) {
    if (detailStatus === 'loading') return <p className="text-sm text-slate-500">Loading...</p>;
    const r = selectedRecipe;
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <button onClick={() => dispatch({ type: 'GO_TO_LIST' })} className="text-slate-500 text-sm hover:text-slate-700">
            ← Back
          </button>
          <h1 className="text-xl font-semibold flex-1">{r.name}</h1>
          <button
            onClick={() => dispatch({ type: 'GO_TO_EDIT' })}
            className="text-sm border border-slate-300 px-3 py-1.5 rounded-lg hover:bg-slate-50"
          >
            Edit
          </button>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Price</span>
            <span className="font-medium">${r.price.toFixed(2)}</span>
          </div>
          {r.description && (
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Description</span>
              <span className="text-slate-700">{r.description}</span>
            </div>
          )}
        </div>

        <div>
          <h2 className="text-sm font-medium text-slate-700 mb-2">Ingredients</h2>
          {r.ingredients.length === 0 ? (
            <p className="text-sm text-slate-500">No ingredients linked.</p>
          ) : (
            <ul className="space-y-1.5">
              {r.ingredients.map((ing) => (
                <li key={ing.link_id} className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-sm flex justify-between">
                  <span className="font-medium">{ing.name}</span>
                  <span className="text-slate-500">
                    {ing.quantity_display ?? (ing.quantity != null ? `${ing.quantity}${ing.unit}` : ing.unit)}
                    {ing.quantity != null && ing.quantity_display && (
                      <span className="text-xs text-slate-400 ml-1">({ing.quantity}{ing.unit})</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        {!deleteConfirm ? (
          <button
            onClick={() => dispatch({ type: 'SET_DELETE_CONFIRM', value: true })}
            className="mt-2 text-sm text-red-500 hover:text-red-700 self-start"
          >
            Delete Recipe
          </button>
        ) : (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 flex items-center gap-3">
            <p className="text-sm text-red-700 flex-1">Delete <strong>{r.name}</strong>? This cannot be undone.</p>
            <button
              onClick={() => dispatch({ type: 'SET_DELETE_CONFIRM', value: false })}
              className="text-sm text-slate-600 border px-2 py-1 rounded"
            >
              Cancel
            </button>
            <button onClick={handleDelete} disabled={loading} className="text-sm bg-red-600 text-white px-2 py-1 rounded disabled:opacity-40">
              {loading ? '...' : 'Delete'}
            </button>
          </div>
        )}
      </div>
    );
  }

  // ── EDIT ─────────────────────────────────────────────────────────────────────
  if (step === STEP.EDIT) {
    const canSave = form.name.trim();
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <button onClick={() => dispatch({ type: 'GO_TO_DETAIL', recipe: selectedRecipe })} className="text-slate-500 text-sm hover:text-slate-700">
            ← Back
          </button>
          <h1 className="text-xl font-semibold">Edit Recipe</h1>
        </div>

        <div className="flex gap-3">
          <div className="flex flex-col gap-1 flex-1">
            <label className="text-xs text-slate-500">Recipe Name *</label>
            <input
              className="border rounded px-2 py-1.5 text-sm"
              value={form.name}
              onChange={(e) => dispatch({ type: 'FORM_UPDATE', field: 'name', value: e.target.value })}
            />
          </div>
          <div className="flex flex-col gap-1 w-28">
            <label className="text-xs text-slate-500">Price ($)</label>
            <input
              className="border rounded px-2 py-1.5 text-sm"
              type="number" min="0" step="0.01"
              value={form.price}
              onChange={(e) => dispatch({ type: 'FORM_UPDATE', field: 'price', value: e.target.value })}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Description (optional)</label>
          <input
            className="border rounded px-2 py-1.5 text-sm"
            value={form.description}
            onChange={(e) => dispatch({ type: 'FORM_UPDATE', field: 'description', value: e.target.value })}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-xs text-slate-500">Ingredients</label>
          {renderIngredientRows()}
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          onClick={handleUpdate}
          disabled={!canSave || loading}
          className="bg-brand text-white px-4 py-2 rounded-lg font-medium disabled:opacity-40"
        >
          {loading ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    );
  }

  // ── LIST ─────────────────────────────────────────────────────────────────────
  if (step === STEP.LIST) {
    return (
      <section className="space-y-4">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Recipes</h1>
            <p className="text-sm text-slate-500">Menu items and their ingredients.</p>
          </div>
          <button
            onClick={() => dispatch({ type: 'GO_TO_INPUT' })}
            className="bg-brand text-white px-3 py-1.5 rounded-lg text-sm font-medium"
          >
            + Add Recipe
          </button>
        </header>

        {listStatus === 'loading' && <p className="text-sm text-slate-500">Loading...</p>}
        {listStatus === 'error' && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{listError}</p>
        )}
        {listStatus === 'ready' && recipes.length === 0 && (
          <p className="text-sm text-slate-500">No recipes yet. Add one to start tracking sales.</p>
        )}

        <ul className="space-y-2">
          {recipes.map((recipe) => (
            <li
              key={recipe.id}
              onClick={() => handleSelectRecipe(recipe.id)}
              className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm cursor-pointer hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">{recipe.name}</p>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-600">${recipe.price.toFixed(2)}</span>
                  <span className="text-xs text-slate-400">›</span>
                </div>
              </div>
              {recipe.description && (
                <p className="mt-1 text-xs text-slate-500">{recipe.description}</p>
              )}
            </li>
          ))}
        </ul>
      </section>
    );
  }

  // ── INPUT ────────────────────────────────────────────────────────────────────
  if (step === STEP.INPUT) {
    const canSave = form.name.trim() && ingredientRows.some((r) => r.ingredientId && r.quantity);

    return (
      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-2">
          <button onClick={() => dispatch({ type: 'GO_TO_LIST' })} className="text-slate-500 text-sm hover:text-slate-700">
            ← Back
          </button>
          <h1 className="text-xl font-semibold">New Recipe</h1>
        </div>

        <div className="flex gap-3">
          <div className="flex flex-col gap-1 flex-1">
            <label className="text-xs text-slate-500">Recipe Name *</label>
            <input
              className="border rounded px-2 py-1.5 text-sm"
              value={form.name}
              onChange={(e) => dispatch({ type: 'FORM_UPDATE', field: 'name', value: e.target.value })}
              placeholder="e.g. Salmon with Cream Sauce"
            />
          </div>
          <div className="flex flex-col gap-1 w-28">
            <label className="text-xs text-slate-500">Price ($)</label>
            <input
              className="border rounded px-2 py-1.5 text-sm"
              type="number" min="0" step="0.01"
              value={form.price}
              onChange={(e) => dispatch({ type: 'FORM_UPDATE', field: 'price', value: e.target.value })}
              placeholder="0.00"
            />
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Description (optional)</label>
          <input
            className="border rounded px-2 py-1.5 text-sm"
            value={form.description}
            onChange={(e) => dispatch({ type: 'FORM_UPDATE', field: 'description', value: e.target.value })}
            placeholder="e.g. Pan-seared salmon in garlic cream sauce"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-xs text-slate-500">Ingredients *</label>
          {renderIngredientRows()}
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          onClick={handleSave}
          disabled={!canSave || loading}
          className="bg-brand text-white px-4 py-2 rounded-lg font-medium disabled:opacity-40"
        >
          {loading ? 'Saving...' : 'Save Recipe'}
        </button>
      </div>
    );
  }

  // ── DONE ─────────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Done</h1>
      <p className="text-lg">
        ✅ Recipe saved — {result?.ingredients_linked ?? 0} ingredients linked,{' '}
        {result?.ingredients_created ?? 0} new ingredients created
      </p>
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <span className="font-medium">{result?.name}</span>
        {result?.price > 0 && (
          <span className="ml-2 text-slate-500">${parseFloat(result.price).toFixed(2)}</span>
        )}
      </div>
      <div className="flex gap-3">
        <button
          onClick={() => dispatch({ type: 'GO_TO_LIST' })}
          className="flex-1 border border-brand text-brand px-4 py-2 rounded-lg font-medium"
        >
          Back to List
        </button>
        <button
          onClick={() => dispatch({ type: 'RESET_FLOW' })}
          className="flex-1 bg-brand text-white px-4 py-2 rounded-lg font-medium"
        >
          Add Another Recipe
        </button>
      </div>
    </div>
  );
}

export default Recipe;
