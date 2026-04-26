import { useState } from 'react';
import { useReceiptFlow, RECEIPT_STEP } from '../hooks/useReceiptFlow.js';
import { useReceiptHistory } from '../hooks/useReceiptHistory.js';
import { ReceiptReviewStep } from '../components/vision/ReceiptReviewStep.jsx';
import { VisionDoneStep } from '../components/vision/VisionDoneStep.jsx';

function Receipt() {
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
  } = useReceiptFlow();

  const { status: histStatus, data: histData, error: histError, refresh } = useReceiptHistory();
  const [expandedDate, setExpandedDate] = useState(null);

  const { step, loading, error, result } = state;

  if (step === RECEIPT_STEP.REVIEW) {
    return (
      <ReceiptReviewStep
        state={state}
        dispatch={dispatch}
        loading={loading}
        error={error}
        onConfirm={handleConfirm}
      />
    );
  }

  if (step === RECEIPT_STEP.DONE) {
    return (
      <VisionDoneStep
        summary={`✅ ${result?.items_processed ?? 0} items recorded, ${result?.items_skipped ?? 0} items skipped`}
        items={result?.items}
        renderItem={(it) => (
          <>
            <span className="rounded px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700">
              Saved
            </span>
            {it.name} — qty {it.quantity}
            {it.ingredients_deducted > 0 && (
              <span className="text-xs text-slate-400">
                ({it.ingredients_deducted} ingredient{it.ingredients_deducted !== 1 ? 's' : ''} deducted)
              </span>
            )}
          </>
        )}
        resetLabel="Scan Another Receipt"
        reset={() => { reset(); refresh(); }}
        navigate={navigate}
      />
    );
  }

  const toggleDate = (date) => setExpandedDate((prev) => (prev === date ? null : date));

  const handleLoadSample = async () => {
    const res = await fetch('/samples/receipt-sample.png');
    const blob = await res.blob();
    handleFileChange(new File([blob], 'receipt-sample.png', { type: 'image/png' }));
  };

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold">Receipt Scan</h1>

      <div
        className="flex items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white px-4 py-3 hover:border-brand transition-colors cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
        onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFileChange(f); }}
        onDragOver={(e) => e.preventDefault()}
      >
        {preview ? (
          <img src={preview} alt="preview" className="h-10 w-10 rounded object-cover shrink-0" />
        ) : (
          <span className="text-2xl shrink-0">🧾</span>
        )}
        <p className="flex-1 truncate text-sm text-slate-600">
          {file ? file.name : 'Click or drag a receipt image'}
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          className="hidden"
          onChange={(e) => e.target.files[0] && handleFileChange(e.target.files[0])}
        />
        <button
          onClick={(e) => { e.stopPropagation(); handleAnalyze(); }}
          disabled={!file || loading}
          className="shrink-0 rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      <div className="flex items-center gap-3 rounded-lg border border-stone-100 bg-stone-50 px-4 py-3">
        <img
          src="/samples/receipt-sample.png"
          alt="sample receipt"
          className="h-14 w-auto rounded border border-stone-200 object-contain shrink-0"
        />
        <div>
          <p className="text-xs text-stone-400">Try with sample image</p>
          <button
            type="button"
            onClick={handleLoadSample}
            className="text-sm text-amber-700 underline hover:text-amber-900"
          >
            Load sample
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {histStatus === 'ready' && histData && (
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">This Week</p>
            <p className="mt-1 text-2xl font-semibold">
              {histData.this_week_total != null ? `$${histData.this_week_total.toFixed(2)}` : '—'}
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">This Month</p>
            <p className="mt-1 text-2xl font-semibold">
              {histData.this_month_total != null ? `$${histData.this_month_total.toFixed(2)}` : '—'}
            </p>
          </div>
        </div>
      )}

      {histStatus === 'loading' && <p className="text-sm text-slate-500">Loading history...</p>}
      {histStatus === 'error' && <p className="text-sm text-red-600">{histError}</p>}

      {histStatus === 'ready' && histData && (
        <div>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-700">Receipt History</h2>
          {histData.receipts.length === 0 ? (
            <p className="text-sm text-slate-500">No receipts scanned yet.</p>
          ) : (
            <ul className="space-y-1">
              {histData.receipts.map((r) => {
                const isOpen = expandedDate === r.date;
                return (
                  <li key={r.date} className="overflow-hidden rounded-md border border-slate-100 bg-white text-sm">
                    <button
                      onClick={() => toggleDate(r.date)}
                      className="grid w-full grid-cols-[1fr_5rem_6rem] items-center px-3 py-2 text-left hover:bg-slate-50 transition-colors"
                    >
                      <span className="font-medium text-slate-700">{r.date}</span>
                      <span className="text-right text-slate-500">{r.item_count} items</span>
                      <span className="flex items-center justify-end gap-1.5 font-medium">
                        {r.total_revenue != null ? `$${r.total_revenue.toFixed(2)}` : '—'}
                        <span className="text-xs text-slate-400">{isOpen ? '▲' : '▼'}</span>
                      </span>
                    </button>
                    {isOpen && (
                      <ul className="divide-y divide-slate-50 border-t border-slate-100">
                        {r.items.map((item, idx) => (
                          <li
                            key={`${item.recipe_name}-${idx}`}
                            className="grid grid-cols-[1fr_5rem_6rem] items-center bg-slate-50 px-3 py-1.5 text-xs text-slate-600"
                          >
                            <span className="truncate pl-2">{item.recipe_name}</span>
                            <span className="text-right text-slate-500">qty {item.quantity}</span>
                            <span className="text-right font-medium">
                              {item.total_price != null ? `$${item.total_price.toFixed(2)}` : '—'}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

export default Receipt;
