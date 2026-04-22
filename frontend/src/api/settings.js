import { get } from './client';

export function checkHealth() {
  return get('/health');
}
