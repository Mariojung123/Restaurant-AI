function RecipeList({ recipes, listStatus, listError, onAddNew, onSelectRecipe }) {
  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Recipes</h1>
          <p className="text-sm text-slate-500">Menu items and their ingredients.</p>
        </div>
        <button
          onClick={onAddNew}
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
            onClick={() => onSelectRecipe(recipe.id)}
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

export default RecipeList;
