import { DASHBOARD_URGENT_DAYS, DASHBOARD_WARNING_DAYS } from '../constants';

export function urgencyLevel(item) {
  if (item.needs_reorder) return 'reorder';
  if (item.days_remaining == null) return 'no-data';
  if (item.days_remaining <= DASHBOARD_URGENT_DAYS) return 'urgent';
  if (item.days_remaining <= DASHBOARD_WARNING_DAYS) return 'warning';
  return 'ok';
}

export function isUrgent(item) {
  const level = urgencyLevel(item);
  return level === 'reorder' || level === 'urgent';
}
