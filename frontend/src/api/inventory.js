import { get } from './client';

export function getForecast() {
  return get('/api/inventory/forecast');
}
