import { useReducer } from 'react';
import { useNavigate } from 'react-router-dom';
import { previewInvoice, confirmInvoice } from '../api/vision.js';
import { ImageUploadZone } from '../components/ImageUploadZone.jsx';
import { useVisionUpload } from '../hooks/useVisionUpload.js';

const STEP = { UPLOAD: 'upload', REVIEW: 'review', DONE: 'done' };

const initialState = {
  step: STEP.UPLOAD,
  items: [],
  supplier: '',
  invoiceDate: '',
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
        supplier: action.supplier,
        invoiceDate: action.invoiceDate,
        duplicateWarning: action.duplicateWarning,
        items: action.items,
      };
    case 'CONFIRM_START':
      return { ...state, loading: true, error: '' };
    case 'CONFIRM_SUCCESS':
      return { ...state, loading: false, step: STEP.DONE, result: action.result };
    case 'REQUEST_ERROR':
      return { ...state, loading: false, error: action.error };
    case 'SET_FIELD':
      return { ...state, [action.field]: action.value };
    case 'UPDATE_ITEM':
      return {
        ...state,
        items: state.items.map((it, i) =>
          i === action.idx ? { ...it, [action.field]: action.value } : it
        ),
      };
    case 'SET_MATCH':
      return {
        ...state,
        items: state.items.map((it, i) => {
          if (i !== action.idx) return it;
          return action.value === '__new__'
            ? { ...it, ingredient_id: null, _useNew: true }
            : { ...it, ingredient_id: parseInt(action.value, 10), _useNew: false };
        }),
      };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

function Invoice() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { step, items, supplier, invoiceDate, duplicateWarning, loading, result, error } = state;
  const { file, preview, fileInputRef, handleFileChange, reset: resetUpload } = useVisionUpload();
  const navigate = useNavigate();

  async function handleAnalyze() {
    if (!file) return;
    dispatch({ type: 'ANALYZE_START' });
    try {
      const data = await previewInvoice(file);
      dispatch({
        type: 'ANALYZE_SUCCESS',
        supplier: data.supplier ?? '',
        invoiceDate: data.invoice_date ?? '',
        duplicateWarning: data.duplicate_warning,
        items: data.items.map((it) => ({
          ...it,
          include: true,
          ingredient_id: it.suggested_match?.id ?? null,
          _useNew: !it.suggested_match || it.match_score < 0.7,
        })),
      });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleConfirm() {
    dispatch({ type: 'CONFIRM_START' });
    try {
      const data = await confirmInvoice({
        supplier: supplier || null,
        invoice_date: invoiceDate || null,
        items: items.map((it) => ({
          name: it.name,
          quantity: parseFloat(it.quantity),
          unit: it.unit,
          unit_price: it.unit_price ? parseFloat(it.unit_price) : null,
          ingredient_id: it.include && !it._useNew ? it.ingredient_id : null,
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

  function matchBadge(item, idx) {
    if (!item.include) return null;
    if (item.match_score === 1.0) {
      return <span className="text-xs text-green-600 font-medium">✓ Matched</span>;
    }
    if (item.match_score >= 0.7) {
      return (
        <select
          className="text-xs border rounded px-1 py-0.5 text-yellow-700 bg-yellow-50"
          value={item._useNew ? '__new__' : String(item.ingredient_id ?? '__new__')}
          onChange={(e) => dispatch({ type: 'SET_MATCH', idx, value: e.target.value })}
        >
          {item.suggested_match && (
            <option value={String(item.suggested_match.id)}>
              {item.suggested_match.name}
            </option>
          )}
          <option value="__new__">Create new</option>
        </select>
      );
    }
    return <span className="text-xs text-blue-600 font-medium">✨ New ingredient</span>;
  }

  if (step === STEP.UPLOAD) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-xl font-semibold">Invoice Scan</h1>
        <ImageUploadZone
          preview={preview}
          fileInputRef={fileInputRef}
          onFile={handleFileChange}
          icon="📄"
          hint="Click or drag an image here"
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
            ⚠ This invoice appears to already be saved. Confirming again will duplicate your stock.
          </div>
        )}
        <div className="flex gap-3">
          <div className="flex flex-col gap-1 flex-1">
            <label className="text-xs text-slate-500">Supplier</label>
            <input
              className="border rounded px-2 py-1 text-sm"
              value={supplier}
              onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'supplier', value: e.target.value })}
            />
          </div>
          <div className="flex flex-col gap-1 flex-1">
            <label className="text-xs text-slate-500">Invoice Date</label>
            <input
              className="border rounded px-2 py-1 text-sm"
              value={invoiceDate}
              onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'invoiceDate', value: e.target.value })}
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b text-left text-xs text-slate-500">
                <th className="pb-2 pr-2">☑</th>
                <th className="pb-2 pr-2">Ingredient</th>
                <th className="pb-2 pr-2">Qty</th>
                <th className="pb-2 pr-2">Unit</th>
                <th className="pb-2 pr-2">Price</th>
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
                      className="border rounded px-1 py-0.5 w-16 text-xs"
                      value={item.quantity}
                      onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'quantity', value: e.target.value })}
                    />
                  </td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-14 text-xs"
                      value={item.unit}
                      onChange={(e) => dispatch({ type: 'UPDATE_ITEM', idx, field: 'unit', value: e.target.value })}
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
                  <td className="py-1.5">{matchBadge(item, idx)}</td>
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
          {loading ? 'Saving...' : 'Update Inventory'}
        </button>
      </div>
    );
  }

  const skipped = result ? items.length - result.items_processed : 0;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Done</h1>
      <p className="text-lg">
        ✅ {result?.items_processed ?? 0} items added to inventory, {skipped} skipped
      </p>
      <ul className="flex flex-col gap-2">
        {result?.items?.map((it, i) => (
          <li key={i} className="flex items-center gap-2 text-sm">
            <span
              className={[
                'rounded px-2 py-0.5 text-xs font-medium',
                it.action === 'matched' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700',
              ].join(' ')}
            >
              {it.action === 'matched' ? 'Existing' : 'New'}
            </span>
            {it.name} — {it.quantity} {it.unit}
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
          Scan Another Invoice
        </button>
      </div>
    </div>
  );
}

export default Invoice;
