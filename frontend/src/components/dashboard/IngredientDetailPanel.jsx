import { memo, useState } from 'react';
import { DASHBOARD_GAUGE_MULTIPLIER, DASHBOARD_LOOKBACK_OPTIONS } from '../../constants';
import { useIngredientDetail } from '../../hooks/useIngredientDetail';
import { formatStock, formatPurchaseDate } from './ForecastCard';

function UsageBar({ amount, max }) {
  const pct = max > 0 ? (amount / max) * 100 : 0;
  return (
    <div className="h-2 rounded-full overflow-hidden">
      <div className="h-full rounded-full bg-blue-400 transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}

function StockGauge({ currentStock, reorderThreshold, unit, lastPurchaseDate }) {
  const denominator = reorderThreshold * DASHBOARD_GAUGE_MULTIPLIER;
  const fillPct = denominator > 0 ? Math.min((currentStock / denominator) * 100, 100) : 0;
  const markerPct = denominator > 0 ? Math.min((reorderThreshold / denominator) * 100, 100) : 50;

  return (
    <div className="space-y-1">
      <div className="relative h-3 rounded-full overflow-visible">
        <div className="h-full rounded-full bg-emerald-400 transition-all" style={{ width: `${fillPct}%` }} />
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
      await onSave(stock, threshold, item);
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
      await onDeleted(ingredientId);
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

function IngredientDetailPanel({ item, onClose, onUpdate, onDelete }) {
  const {
    history,
    historyStatus,
    lookbackDays,
    setLookbackDays,
    showEdit,
    setShowEdit,
    showDeleteConfirm,
    setShowDeleteConfirm,
    maxAmount,
    hasData,
    handleSave,
    handleDelete,
  } = useIngredientDetail(item.ingredient_id, onUpdate, onDelete);

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-blue-900">{item.ingredient_name}</h3>
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
        {DASHBOARD_LOOKBACK_OPTIONS.map((days) => (
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
          onSave={handleSave}
          onCancel={() => setShowEdit(false)}
        />
      )}

      {!showEdit && (
        <div className="border-t border-blue-200 pt-3">
          {showDeleteConfirm ? (
            <DeleteConfirm
              ingredientId={item.ingredient_id}
              onDeleted={handleDelete}
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

export default memo(IngredientDetailPanel);
