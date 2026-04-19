import { get, post } from './client';

export function listRecipes() {
  return get('/api/recipe/');
}

export function previewRecipe(payload) {
  return post('/api/recipe/preview', payload);
}

export function confirmRecipe(payload) {
  return post('/api/recipe/confirm', payload);
}
