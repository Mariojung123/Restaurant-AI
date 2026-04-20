import { get } from './client';

export function getForecast() {
  return get('/api/inventory/forecast');
}

export function getIngredientHistory(ingredientId, lookbackDays = 14) {
  return get(`/api/inventory/history/${ingredientId}?lookback_days=${lookbackDays}`);
}
