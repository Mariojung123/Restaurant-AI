import { useInvoiceFlow, INVOICE_STEP } from '../hooks/useInvoiceFlow.js';
import { ImageUploadZone } from '../components/ImageUploadZone.jsx';
import { MatchBadge } from '../components/MatchBadge.jsx';

function UploadStep({ preview, fileInputRef, handleFileChange, file, loading, error, handleAnalyze }) {
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

function ReviewStep({ state, dispatch, loading, error, handleConfirm }) {
  const { items, supplier, invoiceDate, duplicateWarning } = state;
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
                <td className="py-1.5">
                  <MatchBadge
                    item={item}
                    idx={idx}
                    dispatch={dispatch}
                    selectValue={item._useNew ? '__new__' : String(item.ingredient_id ?? '__new__')}
                    fallbackOption="Create new"
                    fallbackValue="__new__"
                    noMatchLabel="✨ New ingredient"
                    noMatchClass="text-blue-600"
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
        {loading ? 'Saving...' : 'Update Inventory'}
      </button>
    </div>
  );
}

function DoneStep({ state, reset, navigate }) {
  const { result, items } = state;
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

function Invoice() {
  const {
    state,
    dispatch,
    file,
    preview,
    fileInputRef,
    handleFileChange,
    handleAnalyze,
    handleConfirm,
    reset,
    navigate,
  } = useInvoiceFlow();

  const { step, loading, error } = state;

  if (step === INVOICE_STEP.UPLOAD) {
    return (
      <UploadStep
        preview={preview}
        fileInputRef={fileInputRef}
        handleFileChange={handleFileChange}
        file={file}
        loading={loading}
        error={error}
        handleAnalyze={handleAnalyze}
      />
    );
  }

  if (step === INVOICE_STEP.REVIEW) {
    return (
      <ReviewStep
        state={state}
        dispatch={dispatch}
        loading={loading}
        error={error}
        handleConfirm={handleConfirm}
      />
    );
  }

  return <DoneStep state={state} reset={reset} navigate={navigate} />;
}

export default Invoice;
