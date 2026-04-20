import { get, post, put, del } from './client';

export function listRecipes() {
  return get('/api/recipe/');
}

export function getRecipe(id) {
  return get(`/api/recipe/${id}`);
}

export function previewRecipe(payload) {
  return post('/api/recipe/preview', payload);
}

export function confirmRecipe(payload) {
  return post('/api/recipe/confirm', payload);
}

export function updateRecipe(id, payload) {
  return put(`/api/recipe/${id}`, payload);
}

export function deleteRecipe(id) {
  return del(`/api/recipe/${id}`);
}
