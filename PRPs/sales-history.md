# PRP: Sales History

## Goal
Read-only sales summary page — aggregates `sales_logs` by date and menu item with a period filter.

## Endpoint
`GET /api/sales?period_days=7`

Query param `period_days`: integer, `ge=1 le=30`, default `7`.

Response:
```json
{
  "period_days": 7,
  "total_revenue": 1250.00,
  "total_items_sold": 42,
  "daily_summaries": [
    { "date": "2026-04-25", "revenue": 180.00, "items_sold": 6 }
  ],
  "menu_summaries": [
    { "recipe_id": 1, "recipe_name": "Bibimbap", "quantity": 15, "revenue": 450.00 }
  ]
}
```

## Files Changed
| File | Change |
|------|--------|
| `backend/routers/sales.py` | New — GET /api/sales endpoint |
| `backend/services/sales_svc.py` | New — `get_sales_summary(db, period_days)` |
| `backend/main.py` | Register `sales.router` at `/api/sales` |
| `backend/services/constants.py` | Add `SALES_DEFAULT_PERIOD_DAYS = 7`, `SALES_MAX_PERIOD_DAYS = 30` |
| `backend/tests/test_sales.py` | New — test prefix `sal-` |
| `frontend/src/api/sales.js` | New — `fetchSalesSummary(periodDays)` |
| `frontend/src/hooks/useSalesHistory.js` | New — status/data/periodDays state + cancelled guard |
| `frontend/src/pages/Sales.jsx` | New — period filter + summary bar + menu table + daily list |
| `frontend/src/App.jsx` | Add `/sales` route |
| `frontend/src/components/Navbar.jsx` | Add `Sales` nav link |
| `frontend/src/constants.js` | Add `SALES_PERIOD_OPTIONS`, `SALES_DEFAULT_PERIOD_DAYS` |

## Key Rules

### Backend
- All DB queries in `sales_svc.py` — zero DB access in router
- Cutoff: `datetime.now(timezone.utc) - timedelta(days=period_days)`
- ORM join `SalesLog → Recipe` via `SalesLog.recipe` relationship — no raw SQL
- `total_price NULL` → treat as `0.0` (use `coalesce` or Python-side `or 0.0`)
- `daily_summaries` grouped by UTC date, ordered newest-first, zero-sales days omitted
- `menu_summaries` ordered by `quantity` descending
- Router uses `Query(default=SALES_DEFAULT_PERIOD_DAYS, ge=1, le=SALES_MAX_PERIOD_DAYS)` from fastapi

### Frontend
- `useSalesHistory.js`: refetch on `periodDays` change; `cancelled = true` cleanup in useEffect
- `Sales.jsx` states: `loading` / `error` / `ready+empty` / `ready+data`
- Period buttons use `SALES_PERIOD_OPTIONS` from `constants.js` — no hardcoded labels in JSX
- `SALES_DEFAULT_PERIOD_DAYS` imported from `constants.js` as hook default

### Testing (`test_sales.py`, prefix `sal-`)
1. Empty DB → zeros, empty lists
2. Sales within period → correct aggregation
3. Sales outside period → excluded
4. `total_price = NULL` → counted as `0.0`, not skipped
5. `period_days=1` → today only
6. `period_days=30` → 30-day window

Use `client` fixture for HTTP tests. `db_session.flush()` only, never `commit()`.
