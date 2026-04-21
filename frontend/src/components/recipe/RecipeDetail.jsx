function RecipeDetail({
  recipe, detailStatus, deleteConfirm, loading, error,
  onBack, onEdit, onSetDeleteConfirm, onDelete,
}) {
  if (detailStatus === 'loading') return <p className="text-sm text-slate-500">Loading...</p>;

  const r = recipe;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <button onClick={onBack} className="text-slate-500 text-sm hover:text-slate-700">
          ← Back
        </button>
        <h1 className="text-xl font-semibold flex-1">{r.name}</h1>
        <button
          onClick={onEdit}
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
          onClick={() => onSetDeleteConfirm(true)}
          className="mt-2 text-sm text-red-500 hover:text-red-700 self-start"
        >
          Delete Recipe
        </button>
      ) : (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 flex items-center gap-3">
          <p className="text-sm text-red-700 flex-1">Delete <strong>{r.name}</strong>? This cannot be undone.</p>
          <button
            onClick={() => onSetDeleteConfirm(false)}
            className="text-sm text-slate-600 border px-2 py-1 rounded"
          >
            Cancel
          </button>
          <button
            onClick={onDelete}
            disabled={loading}
            className="text-sm bg-red-600 text-white px-2 py-1 rounded disabled:opacity-40"
          >
            {loading ? '...' : 'Delete'}
          </button>
        </div>
      )}
    </div>
  );
}

export default RecipeDetail;
