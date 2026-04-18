import { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const EMPTY_FORM = { name: '', price: '', description: '', ingredientText: '' };

function Recipe() {
  const [step, setStep] = useState(0); // 0=list, 1=input, 2=review, 3=done
  const [recipes, setRecipes] = useState([]);
  const [listStatus, setListStatus] = useState('loading');
  const [listError, setListError] = useState(null);

  const [form, setForm] = useState(EMPTY_FORM);
  const [items, setItems] = useState([]);
  const [previewMeta, setPreviewMeta] = useState(null); // {name, description, price}
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (step !== 0) return;
    let cancelled = false;
    setListStatus('loading');

    fetch(`${API}/api/recipe/`)
      .then((r) => {
        if (!r.ok) throw new Error(`Status ${r.status}`);
        return r.json();
      })
      .then((data) => { if (!cancelled) { setRecipes(data); setListStatus('ready'); } })
      .catch((e) => { if (!cancelled) { setListError(e.message); setListStatus('error'); } });

    return () => { cancelled = true; };
  }, [step]);

  function updateForm(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateItem(idx, field, value) {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, [field]: value } : it)));
  }

  function handleMatchSelect(idx, value) {
    if (value === '__new__') {
      setItems((prev) =>
        prev.map((it, i) => (i === idx ? { ...it, ingredient_id: null, _useNew: true } : it))
      );
    } else {
      const id = parseInt(value, 10);
      setItems((prev) =>
        prev.map((it, i) =>
          i === idx ? { ...it, ingredient_id: id, _useNew: false } : it
        )
      );
    }
  }

  async function handleAnalyze() {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/recipe/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          description: form.description || null,
          price: parseFloat(form.price) || 0,
          ingredient_text: form.ingredientText,
        }),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail ?? res.statusText);
      }
      const data = await res.json();
      setPreviewMeta({ name: data.name, description: data.description, price: data.price });
      setItems(
        data.items.map((it) => ({
          ...it,
          include: true,
          ingredient_id: it.suggested_match?.id ?? null,
          _useNew: !it.suggested_match || it.match_score < 0.7,
        }))
      );
      setStep(2);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setLoading(true);
    setError('');
    try {
      const payload = {
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
      };
      const res = await fetch(`${API}/api/recipe/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail ?? res.statusText);
      }
      const data = await res.json();
      setResult(data);
      setStep(3);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setForm(EMPTY_FORM);
    setItems([]);
    setPreviewMeta(null);
    setResult(null);
    setError('');
    setStep(1);
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
          onChange={(e) => handleMatchSelect(idx, e.target.value)}
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

  // ── Step 0: list ─────────────────────────────────────────────────────────────
  if (step === 0) {
    return (
      <section className="space-y-4">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Recipes</h1>
            <p className="text-sm text-slate-500">Menu items and their ingredients.</p>
          </div>
          <button
            onClick={() => { setError(''); setStep(1); }}
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

  // ── Step 1: input form ───────────────────────────────────────────────────────
  if (step === 1) {
    const canAnalyze = form.name.trim() && form.ingredientText.trim();
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <button onClick={() => setStep(0)} className="text-slate-500 text-sm hover:text-slate-700">
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
              onChange={(e) => updateForm('name', e.target.value)}
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
              onChange={(e) => updateForm('price', e.target.value)}
              placeholder="0.00"
            />
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Description (optional)</label>
          <input
            className="border rounded px-2 py-1.5 text-sm"
            value={form.description}
            onChange={(e) => updateForm('description', e.target.value)}
            placeholder="e.g. Pan-seared salmon in garlic cream sauce"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Ingredients *</label>
          <textarea
            className="border rounded px-2 py-1.5 text-sm min-h-[100px]"
            value={form.ingredientText}
            onChange={(e) => updateForm('ingredientText', e.target.value)}
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

  // ── Step 2: review table ─────────────────────────────────────────────────────
  if (step === 2) {
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <button onClick={() => setStep(1)} className="text-slate-500 text-sm hover:text-slate-700">
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
                      onChange={(e) => updateItem(idx, 'include', e.target.checked)}
                    />
                  </td>
                  <td className="py-1.5 pr-2 text-xs text-slate-700">{item.name}</td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-16 text-xs"
                      value={item.quantity ?? ''}
                      onChange={(e) => updateItem(idx, 'quantity', e.target.value)}
                    />
                  </td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-14 text-xs"
                      value={item.unit}
                      onChange={(e) => updateItem(idx, 'unit', e.target.value)}
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

  // ── Step 3: done ─────────────────────────────────────────────────────────────
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
          onClick={() => setStep(0)}
          className="flex-1 border border-brand text-brand px-4 py-2 rounded-lg font-medium"
        >
          Back to List
        </button>
        <button
          onClick={reset}
          className="flex-1 bg-brand text-white px-4 py-2 rounded-lg font-medium"
        >
          Add Another Recipe
        </button>
      </div>
    </div>
  );
}

export default Recipe;
