import { get, patch, del } from './client';

export function listIngredients() {
  return get('/api/inventory/ingredients');
}

export function getForecast() {
  return get('/api/inventory/forecast');
}

export function getIngredientHistory(ingredientId, lookbackDays = 14) {
  return get(`/api/inventory/history/${ingredientId}?lookback_days=${lookbackDays}`);
}

export function updateIngredient(id, payload) {
  return patch(`/api/inventory/ingredients/${id}`, payload);
}

export function deleteIngredient(id) {
  return del(`/api/inventory/ingredients/${id}`);
}
