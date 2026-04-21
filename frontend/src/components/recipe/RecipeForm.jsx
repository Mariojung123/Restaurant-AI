function IngredientRows({ ingredientRows, ingredients, units, onRowIngredientChange, onUpdateRow, onRemoveRow, onAddRow }) {
  const usedIds = new Set(ingredientRows.map((r) => r.ingredientId).filter(Boolean));
  return (
    <>
      {ingredientRows.map((row, idx) => (
        <div key={idx} className="flex gap-2 items-center">
          <select
            className="flex-1 border rounded px-2 py-1.5 text-sm text-slate-700 bg-white"
            value={row.ingredientId}
            onChange={(e) => onRowIngredientChange(idx, e.target.value)}
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
            onChange={(e) => onUpdateRow(idx, 'quantity', e.target.value)}
          />
          <select
            className="w-20 border rounded px-2 py-1.5 text-sm bg-white"
            value={row.unit}
            onChange={(e) => onUpdateRow(idx, 'unit', e.target.value)}
          >
            {units.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
          <button
            onClick={() => onRemoveRow(idx)}
            disabled={ingredientRows.length === 1}
            className="text-slate-400 hover:text-red-500 disabled:opacity-20 text-lg leading-none px-1"
          >
            ✕
          </button>
        </div>
      ))}
      <button
        onClick={onAddRow}
        className="self-start text-sm text-brand hover:underline mt-1"
      >
        + Add Ingredient
      </button>
    </>
  );
}

function RecipeForm({
  mode, form, ingredientRows, ingredients, units, loading, error,
  onBack, onFormUpdate, onSave, onAddRow, onRemoveRow, onUpdateRow, onRowIngredientChange,
}) {
  const isEdit = mode === 'edit';
  const canSave = isEdit
    ? form.name.trim()
    : form.name.trim() && ingredientRows.some((r) => r.ingredientId && r.quantity);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <button onClick={onBack} className="text-slate-500 text-sm hover:text-slate-700">
          ← Back
        </button>
        <h1 className="text-xl font-semibold">{isEdit ? 'Edit Recipe' : 'New Recipe'}</h1>
      </div>

      <div className="flex gap-3">
        <div className="flex flex-col gap-1 flex-1">
          <label className="text-xs text-slate-500">Recipe Name *</label>
          <input
            className="border rounded px-2 py-1.5 text-sm"
            value={form.name}
            onChange={(e) => onFormUpdate('name', e.target.value)}
            placeholder={isEdit ? undefined : 'e.g. Salmon with Cream Sauce'}
          />
        </div>
        <div className="flex flex-col gap-1 w-28">
          <label className="text-xs text-slate-500">Price ($)</label>
          <input
            className="border rounded px-2 py-1.5 text-sm"
            type="number" min="0" step="0.01"
            value={form.price}
            onChange={(e) => onFormUpdate('price', e.target.value)}
            placeholder={isEdit ? undefined : '0.00'}
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs text-slate-500">Description (optional)</label>
        <input
          className="border rounded px-2 py-1.5 text-sm"
          value={form.description}
          onChange={(e) => onFormUpdate('description', e.target.value)}
          placeholder={isEdit ? undefined : 'e.g. Pan-seared salmon in garlic cream sauce'}
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-slate-500">Ingredients {isEdit ? '' : '*'}</label>
        <IngredientRows
          ingredientRows={ingredientRows}
          ingredients={ingredients}
          units={units}
          onRowIngredientChange={onRowIngredientChange}
          onUpdateRow={onUpdateRow}
          onRemoveRow={onRemoveRow}
          onAddRow={onAddRow}
        />
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <button
        onClick={onSave}
        disabled={!canSave || loading}
        className="bg-brand text-white px-4 py-2 rounded-lg font-medium disabled:opacity-40"
      >
        {loading ? 'Saving...' : isEdit ? 'Save Changes' : 'Save Recipe'}
      </button>
    </div>
  );
}

export default RecipeForm;
