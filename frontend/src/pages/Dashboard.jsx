import { useEffect, useState } from 'react';
import { getForecast, getIngredientHistory } from '../api/inventory';

function formatStock(value, unit) {
  if (unit === 'g' && value >= 1000) return `${+((value / 1000).toFixed(3))}kg`;
  if (unit === 'mL' && value >= 1000) return `${+((value / 1000).toFixed(3))}L`;
  return `${+(value.toFixed(3))}${unit}`;
}

const URGENT_DAYS = 7;
const WARNING_DAYS = 14;
const LOOKBACK_DAYS = 14;

function isUrgent(item) {
  const level = urgencyLevel(item);
  return level === 'reorder' || level === 'urgent';
}

function urgencyLevel(item) {
  if (item.needs_reorder) return 'reorder';
  if (item.days_remaining == null) return 'no-data';
  if (item.days_remaining <= URGENT_DAYS) return 'urgent';
  if (item.days_remaining <= WARNING_DAYS) return 'warning';
  return 'ok';
}

function StatusBadge({ item }) {
  const level = urgencyLevel(item);

  const styles = {
    reorder:  'bg-red-100 text-red-700',
    urgent:   'bg-red-100 text-red-700',
    warning:  'bg-yellow-100 text-yellow-700',
    ok:       'bg-emerald-100 text-emerald-700',
    'no-data':'bg-slate-100 text-slate-500',
  };

  const label =
    level === 'no-data'
      ? 'No sales data'
      : level === 'reorder'
      ? `Reorder now`
      : `${item.days_remaining.toFixed(1)} days left`;

  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[level]}`}>
      {label}
    </span>
  );
}

function DepletionDate({ item }) {
  if (!item.depletion_date) return null;
  const date = new Date(item.depletion_date);
  const formatted = date.toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
  return <span className="text-xs text-slate-400">runs out {formatted}</span>;
}

function UsageBar({ amount, max }) {
  const pct = max > 0 ? (amount / max) * 100 : 0;
  return (
    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
      <div
        className="h-full rounded-full bg-blue-400 transition-all"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function IngredientHistoryPanel({ ingredientId, ingredientName, onClose }) {
  const [history, setHistory] = useState([]);
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let cancelled = false;
    getIngredientHistory(ingredientId)
      .then((data) => { if (!cancelled) { setHistory(data); setStatus('ready'); } })
      .catch(() => { if (!cancelled) setStatus('error'); });
    return () => { cancelled = true; };
  }, [ingredientId]);

  const maxAmount = Math.max(...history.map((r) => r.amount), 0.001);
  const hasData = history.some((r) => r.amount > 0);

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-blue-900">
          {ingredientName} — 14-day usage
        </h3>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 text-lg leading-none"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      {status === 'loading' && (
        <p className="text-xs text-slate-500">Loading...</p>
      )}
      {status === 'error' && (
        <p className="text-xs text-red-600">Failed to load history.</p>
      )}
      {status === 'ready' && !hasData && (
        <p className="text-xs text-slate-500">No sales data in this period.</p>
      )}
      {status === 'ready' && hasData && (
        <ul className="space-y-1.5">
          {history.map((row) => (
            <li key={row.date} className="grid grid-cols-[5rem_1fr_3rem] items-center gap-2">
              <span className="text-xs text-slate-500 text-right">{row.date.slice(5)}</span>
              <UsageBar amount={row.amount} max={maxAmount} />
              <span className="text-xs text-slate-600 text-right">{row.amount.toFixed(1)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ForecastCard({ item, isSelected, onSelect }) {
  const level = urgencyLevel(item);
  const borderColor = {
    reorder:  'border-red-300',
    urgent:   'border-red-300',
    warning:  'border-yellow-300',
    ok:       'border-slate-200',
    'no-data':'border-slate-200',
  }[level];

  return (
    <li
      className={`flex items-center justify-between rounded-lg border ${borderColor} bg-white px-4 py-3 shadow-sm cursor-pointer hover:bg-slate-50 transition-colors ${isSelected ? 'ring-2 ring-blue-300' : ''}`}
      onClick={onSelect}
    >
      <div className="space-y-0.5">
        <p className="text-sm font-medium">{item.ingredient_name}</p>
        <p className="text-xs text-slate-500">
          Stock: {formatStock(item.current_stock, item.unit)} | Daily use: {formatStock(item.daily_consumption, item.unit)}
        </p>
        <DepletionDate item={item} />
      </div>
      <StatusBadge item={item} />
    </li>
  );
}

function Dashboard() {
  const [forecast, setForecast] = useState([]);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadForecast() {
      try {
        const data = await getForecast();
        if (!cancelled) {
          setForecast(data);
          setStatus('ready');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setStatus('error');
        }
      }
    }

    loadForecast();
    return () => { cancelled = true; };
  }, []);

  function handleSelectItem(item) {
    setSelectedItem((prev) =>
      prev?.ingredient_id === item.ingredient_id ? null : item
    );
  }

  const reorderItems = forecast.filter(isUrgent);
  const otherItems   = forecast.filter((i) => !isUrgent(i));

  function renderList(items) {
    return (
      <ul className="space-y-2">
        {items.map((item) => (
          <div key={item.ingredient_id} className="space-y-2">
            <ForecastCard
              item={item}
              isSelected={selectedItem?.ingredient_id === item.ingredient_id}
              onSelect={() => handleSelectItem(item)}
            />
            {selectedItem?.ingredient_id === item.ingredient_id && (
              <IngredientHistoryPanel
                ingredientId={item.ingredient_id}
                ingredientName={item.ingredient_name}
                onClose={() => setSelectedItem(null)}
              />
            )}
          </div>
        ))}
      </ul>
    );
  }

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold">Inventory forecast</h1>
        <p className="text-sm text-slate-500">
          Projected depletion based on last {LOOKBACK_DAYS} days of sales. Click an ingredient to see daily usage.
        </p>
      </header>

      {status === 'loading' && <p className="text-sm text-slate-500">Loading...</p>}
      {status === 'error' && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {status === 'ready' && forecast.length === 0 && (
        <p className="text-sm text-slate-500">No ingredients tracked yet.</p>
      )}

      {status === 'ready' && reorderItems.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-red-600 uppercase tracking-wide">
            ⚠ Needs attention
          </h2>
          {renderList(reorderItems)}
        </div>
      )}

      {status === 'ready' && otherItems.length > 0 && (
        <div className="space-y-2">
          {reorderItems.length > 0 && (
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">All ingredients</h2>
          )}
          {renderList(otherItems)}
        </div>
      )}
    </section>
  );
}

export default Dashboard;
