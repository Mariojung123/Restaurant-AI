import { MatchBadge } from '../MatchBadge.jsx';
import { MATCH_SENTINEL } from '../../constants.js';

export function ReceiptReviewStep({ state, dispatch, loading, error, onConfirm }) {
  const { saleDate, items, duplicateWarning } = state;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Review & Edit</h1>
      {duplicateWarning && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-3 text-sm text-yellow-800">
          ⚠ Sales data for this date already exists. Confirming again will duplicate records.
        </div>
      )}
      <div className="flex flex-col gap-1">
        <label className="text-xs text-slate-500">Sale Date</label>
        <input
          className="border rounded px-2 py-1 text-sm max-w-xs"
          value={saleDate}
          onChange={(e) => dispatch({ type: 'SET_SALE_DATE', value: e.target.value })}
          placeholder="YYYY-MM-DD"
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b text-left text-xs text-slate-500">
              <th className="pb-2 pr-2">☑</th>
              <th className="pb-2 pr-2">Menu Item</th>
              <th className="pb-2 pr-2">Qty</th>
              <th className="pb-2 pr-2">Unit Price</th>
              <th className="pb-2 pr-2">Total</th>
              <th className="pb-2">Match</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr key={idx} className={['border-b', !item.include ? 'opacity-40' : ''].join(' ')}>
                <td className="py-1.5 pr-2">
                  <input
                    type="checkbox"
                    checked={item.include}
                    onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'include', value: e.target.checked })}
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    className="border rounded px-1 py-0.5 w-full text-xs"
                    value={item.name}
                    onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'name', value: e.target.value })}
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    className="border rounded px-1 py-0.5 w-14 text-xs"
                    value={item.quantity}
                    onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'quantity', value: e.target.value })}
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    className="border rounded px-1 py-0.5 w-16 text-xs"
                    value={item.unit_price ?? ''}
                    onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'unit_price', value: e.target.value })}
                    placeholder="—"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    className="border rounded px-1 py-0.5 w-16 text-xs"
                    value={item.total_price ?? ''}
                    onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'total_price', value: e.target.value })}
                    placeholder="—"
                  />
                </td>
                <td className="py-1.5">
                  <MatchBadge
                    item={item}
                    idx={idx}
                    dispatch={dispatch}
                    selectValue={item._pendingRecipeId !== null ? String(item._pendingRecipeId) : MATCH_SENTINEL.SKIP}
                    fallbackOption="Skip"
                    fallbackValue={MATCH_SENTINEL.SKIP}
                    noMatchLabel="✨ No recipe — will skip"
                    noMatchClass="text-slate-400"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      <button
        onClick={onConfirm}
        disabled={loading}
        className="bg-brand text-white px-4 py-2 rounded-lg font-medium disabled:opacity-40"
      >
        {loading ? 'Saving...' : 'Record Sales'}
      </button>
    </div>
  );
}
