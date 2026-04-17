import { useEffect, useState } from 'react';

// Recipe page: lists menu items served by /api/recipe.
function Recipe() {
  const [recipes, setRecipes] = useState([]);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadRecipes() {
      try {
        const response = await fetch('/api/recipe/');
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const data = await response.json();
        if (!cancelled) {
          setRecipes(data);
          setStatus('ready');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setStatus('error');
        }
      }
    }

    loadRecipes();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold">Recipes</h1>
        <p className="text-sm text-slate-500">Menu items and their ingredients.</p>
      </header>

      {status === 'loading' && <p className="text-sm text-slate-500">Loading...</p>}
      {status === 'error' && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}
      {status === 'ready' && recipes.length === 0 && (
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

export default Recipe;
