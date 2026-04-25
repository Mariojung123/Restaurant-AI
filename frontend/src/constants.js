export const FUZZY_MATCH_THRESHOLD = 0.7;

export const DASHBOARD_URGENT_DAYS = 3;
export const DASHBOARD_WARNING_DAYS = 5;
export const DASHBOARD_LOOKBACK_DAYS = 7;
export const DASHBOARD_GAUGE_MULTIPLIER = 5;
export const DASHBOARD_LOOKBACK_OPTIONS = [7, 14];
export const DASHBOARD_DAYS_PER_WEEK = 7;

export const STORAGE_KEY_RESTAURANT_NAME = 'restaurant_name';
export const STORAGE_KEY_CHAT_SESSION = 'chat_session_id';

export const MATCH_SENTINEL = { NEW: '__new__', SKIP: '__skip__' };

export const SALES_PERIOD_OPTIONS = [
  { label: 'Today', days: 1 },
  { label: '7 days', days: 7 },
  { label: '30 days', days: 30 },
];
export const SALES_DEFAULT_PERIOD_DAYS = 7;

export const RECIPE_STEP = { LIST: 'list', INPUT: 'input', DONE: 'done', DETAIL: 'detail', EDIT: 'edit' };
export const RECIPE_UNITS = ['g', 'ml', 'ea', 'tsp', 'tbsp', 'oz', 'cup', 'kg', 'L'];
export const RECIPE_EMPTY_FORM = { name: '', price: '', description: '' };
