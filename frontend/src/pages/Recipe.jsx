import { useEffect, useReducer } from 'react';
import { listRecipes, previewRecipe, confirmRecipe } from '../api/recipe.js';

const STEP = { LIST: 'list', INPUT: 'input', REVIEW: 'review', DONE: 'done' };
const EMPTY_FORM = { name: '', price: '', description: '', ingredientText: '' };

const initialState = {
  step: STEP.LIST,
  // list view
  recipes: [],
  listStatus: 'loading',
  listError: null,
  // registration flow
  form: EMPTY_FORM,
  items: [],
  previewMeta: null,
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
      return { ...state, step: STEP.INPUT, error: '' };
    case 'GO_TO_LIST':
      return { ...state, step: STEP.LIST };
    case 'GO_TO_INPUT_FROM_REVIEW':
      return { ...state, step: STEP.INPUT };
    case 'FORM_UPDATE':
      return { ...state, form: { ...state.form, [action.field]: action.value } };
    case 'ANALYZE_START':
      return { ...state, loading: true, error: '' };
    case 'ANALYZE_SUCCESS':
      return {
        ...state,
        loading: false,
        step: STEP.REVIEW,
        previewMeta: { name: action.name, description: action.description, price: action.price },
        items: action.items,
      };
    case 'SAVE_START':
      return { ...state, loading: true, error: '' };
    case 'SAVE_SUCCESS':
      return { ...state, loading: false, step: STEP.DONE, result: action.result };
    case 'REQUEST_ERROR':
      return { ...state, loading: false, error: action.error };
    case 'UPDATE_ITEM':
      return {
        ...state,
        items: state.items.map((it, i) =>
          i === action.idx ? { ...it, [action.field]: action.value } : it
        ),
      };
    case 'SET_MATCH':
      return {
        ...state,
        items: state.items.map((it, i) => {
          if (i !== action.idx) return it;
          return action.value === '__new__'
            ? { ...it, ingredient_id: null, _useNew: true }
            : { ...it, ingredient_id: parseInt(action.value, 10), _useNew: false };
        }),
      };
    case 'RESET_FLOW':
      return {
        ...state,
        step: STEP.INPUT,
        form: EMPTY_FORM,
        items: [],
        previewMeta: null,
        result: null,
        error: '',
      };
    default:
      return state;
  }
}

function Recipe() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const {
    step, recipes, listStatus, listError,
    form, items, previewMeta, loading, error, result,
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

  async function handleAnalyze() {
    dispatch({ type: 'ANALYZE_START' });
    try {
      const data = await previewRecipe({
        name: form.name,
        description: form.description || null,
        price: parseFloat(form.price) || 0,
        ingredient_text: form.ingredientText,
      });
      dispatch({
        type: 'ANALYZE_SUCCESS',
        name: data.name,
        description: data.description,
        price: data.price,
        items: data.items.map((it) => ({
          ...it,
          include: true,
          ingredient_id: it.suggested_match?.id ?? null,
          _useNew: !it.suggested_match || it.match_score < 0.7,
        })),
      });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleSave() {
    dispatch({ type: 'SAVE_START' });
    try {
      const data = await confirmRecipe({
        name: previewMeta.name,
        description: previewMeta.description,
        price: previewMeta.price,
        items: items.map((it) => ({
          name: it.name,
          quantity: it.quantity ? parseFloat(it.quantity) : null,
          unit: it.unit,
          quantity_display: it.quantity_display,
          ingredient_id: it.include && !it._useNew ? it.ingredient_id : null,
          include: it.include,
        })),
      });
      dispatch({ type: 'SAVE_SUCCESS', result: data });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  function matchBadge(item, idx) {
    if (!item.include) return null;
    if (item.match_score === 1.0) {
      return <span className="text-xs text-green-600 font-medium">✓ Matched</span>;
    }
    if (item.match_score >= 0.7) {
      return (
        <select
          className="text-xs border rounded px-1 py-0.5 text-yellow-700 bg-yellow-50"
          value={item._useNew ? '__new__' : String(item.ingredient_id ?? '__new__')}
          onChange={(e) => dispatch({ type: 'SET_MATCH', idx, value: e.target.value })}
        >
          {item.suggested_match && (
            <option value={String(item.suggested_match.id)}>
              {item.suggested_match.name}
            </option>
          )}
          <option value="__new__">Create new</option>
        </select>
      );
    }
    return <span className="text-xs text-blue-600 font-medium">✨ New ingredient</span>;
  }

  // ── Step LIST ─────────────────────────────────────────────────────────────────
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
              className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">{recipe.name}</p>
                <span className="text-sm text-slate-600">${recipe.price.toFixed(2)}</span>
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

  // ── Step INPUT ───────────────────────────────────────────────────────────────
  if (step === STEP.INPUT) {
    const canAnalyze = form.name.trim() && form.ingredientText.trim();
    return (
      <div className="flex flex-col gap-4">
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
              type="number"
              min="0"
              step="0.01"
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

        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Ingredients *</label>
          <textarea
            className="border rounded px-2 py-1.5 text-sm min-h-[100px]"
            value={form.ingredientText}
            onChange={(e) => dispatch({ type: 'FORM_UPDATE', field: 'ingredientText', value: e.target.value })}
            placeholder="salmon fillet 200g, butter 1 tablespoon, heavy cream 100ml, garlic 2 cloves"
          />
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          onClick={handleAnalyze}
          disabled={!canAnalyze || loading}
          className="bg-brand text-white px-4 py-2 rounded-lg font-medium disabled:opacity-40"
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>
    );
  }

  // ── Step REVIEW ──────────────────────────────────────────────────────────────
  if (step === STEP.REVIEW) {
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <button onClick={() => dispatch({ type: 'GO_TO_INPUT_FROM_REVIEW' })} className="text-slate-500 text-sm hover:text-slate-700">
            ← Back
          </button>
          <h1 className="text-xl font-semibold">Review Ingredients</h1>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
          <span className="font-medium">{previewMeta?.name}</span>
          {previewMeta?.price > 0 && (
            <span className="ml-2 text-slate-500">${parseFloat(previewMeta.price).toFixed(2)}</span>
          )}
          {previewMeta?.description && (
            <p className="text-xs text-slate-500 mt-0.5">{previewMeta.description}</p>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b text-left text-xs text-slate-500">
                <th className="pb-2 pr-2">☑</th>
                <th className="pb-2 pr-2">Ingredient</th>
                <th className="pb-2 pr-2">Qty</th>
                <th className="pb-2 pr-2">Unit</th>
                <th className="pb-2 pr-2">Display</th>
                <th className="pb-2 pr-2">Claude's note</th>
                <th className="pb-2">Match</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr
                  key={idx}
                  className={['border-b', !item.include ? 'opacity-40' : ''].join(' ')}
                >
                  <td className="py-1.5 pr-2">
                    <input
                      type="checkbox"
                      checked={item.include}
                      onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'include', value: e.target.checked })}
                    />
                  </td>
                  <td className="py-1.5 pr-2 text-xs text-slate-700">{item.name}</td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-16 text-xs"
                      value={item.quantity ?? ''}
                      onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'quantity', value: e.target.value })}
                    />
                  </td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-14 text-xs"
                      value={item.unit}
                      onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'unit', value: e.target.value })}
                    />
                  </td>
                  <td className="py-1.5 pr-2 text-xs text-slate-500">{item.quantity_display}</td>
                  <td className="py-1.5 pr-2 text-xs text-slate-400 max-w-[180px]">
                    {item.reasoning}
                  </td>
                  <td className="py-1.5">{matchBadge(item, idx)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          onClick={handleSave}
          disabled={loading}
          className="bg-brand text-white px-4 py-2 rounded-lg font-medium disabled:opacity-40"
        >
          {loading ? 'Saving...' : 'Save Recipe'}
        </button>
      </div>
    );
  }

  // ── Step DONE ─────────────────────────────────────────────────────────────────
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
