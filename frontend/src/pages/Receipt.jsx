import { useReducer } from 'react';
import { useNavigate } from 'react-router-dom';
import { previewReceipt, confirmReceipt } from '../api/vision.js';
import { ImageUploadZone } from '../components/ImageUploadZone.jsx';
import { useVisionUpload } from '../hooks/useVisionUpload.js';
import { MatchBadge } from '../components/MatchBadge.jsx';

const STEP = { UPLOAD: 'upload', REVIEW: 'review', DONE: 'done' };

const initialState = {
  step: STEP.UPLOAD,
  saleDate: '',
  items: [],
  duplicateWarning: false,
  loading: false,
  result: null,
  error: '',
};

function reducer(state, action) {
  switch (action.type) {
    case 'ANALYZE_START':
      return { ...state, loading: true, error: '' };
    case 'ANALYZE_SUCCESS':
      return {
        ...state,
        loading: false,
        step: STEP.REVIEW,
        saleDate: action.saleDate,
        duplicateWarning: action.duplicateWarning,
        items: action.items,
      };
    case 'CONFIRM_START':
      return { ...state, loading: true, error: '' };
    case 'CONFIRM_SUCCESS':
      return { ...state, loading: false, step: STEP.DONE, result: action.result };
    case 'REQUEST_ERROR':
      return { ...state, loading: false, error: action.error };
    case 'SET_SALE_DATE':
      return { ...state, saleDate: action.value };
    case 'UPDATE_ITEM': {
      const updated = state.items.map((it, i) => {
        if (i !== action.idx) return it;
        const next = { ...it, [action.field]: action.value };
        if (action.field === 'quantity' || action.field === 'unit_price') {
          const qty = parseFloat(action.field === 'quantity' ? action.value : it.quantity);
          const price = parseFloat(action.field === 'unit_price' ? action.value : it.unit_price);
          if (!isNaN(qty) && !isNaN(price)) next.total_price = String(+(qty * price).toFixed(2));
        }
        return next;
      });
      return { ...state, items: updated };
    }
    case 'SET_MATCH':
      return {
        ...state,
        items: state.items.map((it, i) => {
          if (i !== action.idx) return it;
          return action.value === '__skip__'
            ? { ...it, recipe_id: null, _pendingRecipeId: null }
            : { ...it, recipe_id: parseInt(action.value, 10), _pendingRecipeId: parseInt(action.value, 10) };
        }),
      };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

function Receipt() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { step, saleDate, items, duplicateWarning, loading, result, error } = state;
  const { file, preview, fileInputRef, handleFileChange, reset: resetUpload } = useVisionUpload();
  const navigate = useNavigate();

  async function handleAnalyze() {
    if (!file) return;
    dispatch({ type: 'ANALYZE_START' });
    try {
      const data = await previewReceipt(file);
      dispatch({
        type: 'ANALYZE_SUCCESS',
        saleDate: data.sale_date ?? '',
        duplicateWarning: data.duplicate_warning,
        items: data.items.map((it) => ({
          ...it,
          include: it.suggested_match !== null,
          recipe_id: it.suggested_match?.id ?? null,
          _pendingRecipeId: it.suggested_match?.id ?? null,
        })),
      });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleConfirm() {
    dispatch({ type: 'CONFIRM_START' });
    try {
      const data = await confirmReceipt({
        sale_date: saleDate || null,
        items: items.map((it) => ({
          name: it.name,
          quantity: parseInt(it.quantity, 10),
          unit_price: it.unit_price ? parseFloat(it.unit_price) : null,
          total_price: it.total_price ? parseFloat(it.total_price) : null,
          recipe_id: it.include ? it.recipe_id : null,
          include: it.include,
        })),
      });
      dispatch({ type: 'CONFIRM_SUCCESS', result: data });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  function reset() {
    resetUpload();
    dispatch({ type: 'RESET' });
  }


  if (step === STEP.UPLOAD) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-xl font-semibold">Receipt Scan</h1>
        <ImageUploadZone
          preview={preview}
          fileInputRef={fileInputRef}
          onFile={handleFileChange}
          icon="🧾"
          hint="Click or drag a receipt image here"
        />
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button
          onClick={handleAnalyze}
          disabled={!file || loading}
          className="bg-brand text-white px-4 py-2 rounded-lg font-medium disabled:opacity-40"
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>
    );
  }

  if (step === STEP.REVIEW) {
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
                <tr
                  key={idx}
                  className={['border-b', !item.include ? 'opacity-40' : ''].join(' ')}
                >
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
                      selectValue={item._pendingRecipeId !== null ? String(item._pendingRecipeId) : '__skip__'}
                      fallbackOption="Skip"
                      fallbackValue="__skip__"
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
          onClick={handleConfirm}
          disabled={loading}
          className="bg-brand text-white px-4 py-2 rounded-lg font-medium disabled:opacity-40"
        >
          {loading ? 'Saving...' : 'Record Sales'}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Done</h1>
      <p className="text-lg">
        ✅ {result?.items_processed ?? 0} items recorded, {result?.items_skipped ?? 0} items skipped
      </p>
      <ul className="flex flex-col gap-2">
        {result?.items?.map((it, i) => (
          <li key={i} className="flex items-center gap-2 text-sm">
            <span className="rounded px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700">
              Saved
            </span>
            {it.name} — qty {it.quantity}
            {it.ingredients_deducted > 0 && (
              <span className="text-xs text-slate-400">
                ({it.ingredients_deducted} ingredient{it.ingredients_deducted !== 1 ? 's' : ''} deducted)
              </span>
            )}
          </li>
        ))}
      </ul>
      <div className="flex gap-3">
        <button
          onClick={() => navigate('/')}
          className="flex-1 border border-brand text-brand px-4 py-2 rounded-lg font-medium"
        >
          Go to Dashboard
        </button>
        <button
          onClick={reset}
          className="flex-1 bg-brand text-white px-4 py-2 rounded-lg font-medium"
        >
          Scan Another Receipt
        </button>
      </div>
    </div>
  );
}

export default Receipt;
