const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function _post(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? res.statusText);
  return data;
}

export async function listRecipes() {
  const res = await fetch(`${API}/api/recipe/`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? res.statusText);
  return data;
}

export function previewRecipe(payload) {
  return _post('/api/recipe/preview', payload);
}

export function confirmRecipe(payload) {
  return _post('/api/recipe/confirm', payload);
}
