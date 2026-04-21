import { useEffect, useState } from 'react';
import { getForecast, getIngredientHistory, updateIngredient, deleteIngredient } from '../api/inventory';

function formatStock(value, unit) {
  if (unit === 'g' && value >= 1000) return `${+((value / 1000).toFixed(3))}kg`;
  if (unit === 'mL' && value >= 1000) return `${+((value / 1000).toFixed(3))}L`;
  return `${+(value.toFixed(3))}${unit}`;
}

function formatWeekly(dailyValue, unit) {
  return `${formatStock(dailyValue * DAYS_PER_WEEK, unit)}/week`;
}

function formatPurchaseDate(isoString) {
  if (!isoString) return 'No record';
  const date = new Date(isoString);
  return date.toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
}

const URGENT_DAYS = 3;
const WARNING_DAYS = 5;
const LOOKBACK_DAYS = 7;
const GAUGE_DENOMINATOR_MULTIPLIER = 5;
const LOOKBACK_OPTIONS = [7, 14];
const DAYS_PER_WEEK = 7;

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
    reorder:   'bg-red-100 text-red-700',
    urgent:    'bg-red-100 text-red-700',
    warning:   'bg-yellow-100 text-yellow-700',
    ok:        'bg-emerald-100 text-emerald-700',
    'no-data': 'bg-slate-100 text-slate-500',
  };
  const label =
    level === 'no-data' ? 'No sales data'
    : level === 'reorder' ? 'Reorder now'
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
      <div className="h-full rounded-full bg-blue-400 transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}

function StockGauge({ currentStock, reorderThreshold, unit, lastPurchaseDate }) {
  const denominator = reorderThreshold * GAUGE_DENOMINATOR_MULTIPLIER;
  const fillPct = denominator > 0 ? Math.min((currentStock / denominator) * 100, 100) : 0;
  const markerPct = denominator > 0 ? Math.min((reorderThreshold / denominator) * 100, 100) : 50;

  return (
    <div className="space-y-1">
      <div className="relative h-3 rounded-full bg-slate-100 overflow-visible">
        <div
          className="h-full rounded-full bg-emerald-400 transition-all"
          style={{ width: `${fillPct}%` }}
        />
        {reorderThreshold > 0 && (
          <div
            className="absolute top-0 h-full w-0.5 bg-red-500"
            style={{ left: `${markerPct}%` }}
            title={`Reorder at ${formatStock(reorderThreshold, unit)}`}
          />
        )}
      </div>
      <p className="text-xs text-slate-500">
        Stock: {formatStock(currentStock, unit)} / Last order: {formatPurchaseDate(lastPurchaseDate)}
      </p>
    </div>
  );
}

function EditForm({ item, onSave, onCancel }) {
  const [stock, setStock] = useState(String(+item.current_stock.toFixed(3)));
  const [threshold, setThreshold] = useState(String(+item.reorder_threshold.toFixed(3)));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateIngredient(item.ingredient_id, {
        current_stock: Number(stock),
        reorder_threshold: Number(threshold),
      });
      onSave();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="border-t border-blue-200 pt-3 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Current stock ({item.unit})</span>
          <input
            type="number"
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            value={stock}
            onChange={(e) => setStock(e.target.value)}
            disabled={saving}
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Reorder threshold ({item.unit})</span>
          <input
            type="number"
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            disabled={saving}
          />
        </label>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button
          onClick={onCancel}
          disabled={saving}
          className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function DeleteConfirm({ ingredientId, onDeleted, onCancel }) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteIngredient(ingredientId);
      onDeleted();
    } catch (err) {
      setError(err.message);
      setDeleting(false);
    }
  }

  return (
    <div className="border-t border-red-200 pt-3 space-y-2">
      <p className="text-xs text-red-700 font-medium">Delete this ingredient permanently?</p>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="rounded bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700 disabled:opacity-50"
        >
          {deleting ? 'Deleting...' : 'Yes, delete'}
        </button>
        <button
          onClick={onCancel}
          disabled={deleting}
          className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          No
        </button>
      </div>
    </div>
  );
}

function IngredientDetailPanel({ ingredientId, ingredientName, item, onClose, onUpdate, onDelete }) {
  const [history, setHistory] = useState([]);
  const [historyStatus, setHistoryStatus] = useState('loading');
  const [lookbackDays, setLookbackDays] = useState(7);
  const [showEdit, setShowEdit] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setHistoryStatus('loading');
    getIngredientHistory(ingredientId, lookbackDays)
      .then((data) => { if (!cancelled) { setHistory(data); setHistoryStatus('ready'); } })
      .catch(() => { if (!cancelled) setHistoryStatus('error'); });
    return () => { cancelled = true; };
  }, [ingredientId, lookbackDays]);

  const maxAmount = Math.max(...history.map((r) => r.amount), 0.001);
  const hasData = history.some((r) => r.amount > 0);

  function handleEditSave() {
    setShowEdit(false);
    onUpdate();
  }

  function handleDeleted() {
    onDelete();
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-blue-900">{ingredientName}</h3>
        <div className="flex items-center gap-2">
          {!showDeleteConfirm && (
            <button
              onClick={() => { setShowEdit((v) => !v); setShowDeleteConfirm(false); }}
              className="rounded border border-blue-300 px-2 py-0.5 text-xs text-blue-700 hover:bg-blue-100"
            >
              {showEdit ? 'Cancel edit' : 'Edit'}
            </button>
          )}
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-lg leading-none"
            aria-label="Close panel"
          >
            ×
          </button>
        </div>
      </div>

      <div className="flex gap-1">
        {LOOKBACK_OPTIONS.map((days) => (
          <button
            key={days}
            onClick={() => setLookbackDays(days)}
            className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
              lookbackDays === days
                ? 'bg-blue-600 text-white'
                : 'border border-blue-300 text-blue-700 hover:bg-blue-100'
            }`}
          >
            {days}d
          </button>
        ))}
      </div>

      {historyStatus === 'loading' && <p className="text-xs text-slate-500">Loading...</p>}
      {historyStatus === 'error' && <p className="text-xs text-red-600">Failed to load history.</p>}
      {historyStatus === 'ready' && !hasData && (
        <p className="text-xs text-slate-500">No sales data in this period.</p>
      )}
      {historyStatus === 'ready' && hasData && (
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

      <StockGauge
        currentStock={item.current_stock}
        reorderThreshold={item.reorder_threshold}
        unit={item.unit}
        lastPurchaseDate={item.last_purchase_date}
      />

      {showEdit && (
        <EditForm
          item={item}
          onSave={handleEditSave}
          onCancel={() => setShowEdit(false)}
        />
      )}

      {!showEdit && (
        <div className="border-t border-blue-200 pt-3">
          {showDeleteConfirm ? (
            <DeleteConfirm
              ingredientId={ingredientId}
              onDeleted={handleDeleted}
              onCancel={() => setShowDeleteConfirm(false)}
            />
          ) : (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="rounded border border-red-300 px-3 py-1 text-xs text-red-600 hover:bg-red-50"
            >
              Delete ingredient
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ForecastCard({ item, isSelected, onSelect }) {
  const level = urgencyLevel(item);
  const borderColor = {
    reorder:   'border-red-300',
    urgent:    'border-red-300',
    warning:   'border-yellow-300',
    ok:        'border-slate-200',
    'no-data': 'border-slate-200',
  }[level];

  return (
    <li
      className={`flex items-center justify-between rounded-lg border ${borderColor} bg-white px-4 py-3 shadow-sm cursor-pointer hover:bg-slate-50 transition-colors ${isSelected ? 'ring-2 ring-blue-300' : ''}`}
      onClick={onSelect}
    >
      <div className="space-y-0.5">
        <p className="text-sm font-medium">{item.ingredient_name}</p>
        <p className="text-xs text-slate-500">
          Stock: {formatStock(item.current_stock, item.unit)} | Weekly use: {formatWeekly(item.daily_consumption, item.unit)}
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

  function loadForecast() {
    let cancelled = false;
    setStatus('loading');
    getForecast()
      .then((data) => { if (!cancelled) { setForecast(data); setStatus('ready'); } })
      .catch((err) => { if (!cancelled) { setError(err.message); setStatus('error'); } });
    return () => { cancelled = true; };
  }

  useEffect(loadForecast, []);

  function handleSelectItem(item) {
    setSelectedItem((prev) => prev?.ingredient_id === item.ingredient_id ? null : item);
  }

  function handleUpdate() {
    setSelectedItem(null);
    loadForecast();
  }

  function handleDelete() {
    setSelectedItem(null);
    loadForecast();
  }

  const LEVEL_ORDER = { reorder: 0, urgent: 0, warning: 1, ok: 2, 'no-data': 3 };
  const reorderItems = forecast.filter(isUrgent);
  const otherItems   = forecast
    .filter((i) => !isUrgent(i))
    .sort((a, b) => LEVEL_ORDER[urgencyLevel(a)] - LEVEL_ORDER[urgencyLevel(b)]);

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
              <IngredientDetailPanel
                ingredientId={item.ingredient_id}
                ingredientName={item.ingredient_name}
                item={item}
                onClose={() => setSelectedItem(null)}
                onUpdate={handleUpdate}
                onDelete={handleDelete}
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
          Projected depletion based on last {LOOKBACK_DAYS} days of sales. Click an ingredient to see weekly usage.
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
          <h2 className="text-sm font-semibold text-red-600 uppercase tracking-wide">⚠ Needs attention</h2>
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
