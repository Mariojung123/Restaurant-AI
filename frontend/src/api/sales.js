import { get } from './client';

export function fetchSalesSummary(periodDays) {
  return get(`/api/sales?period_days=${periodDays}`);
}
