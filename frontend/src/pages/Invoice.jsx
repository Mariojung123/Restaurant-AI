import { useState } from 'react';
import { useInvoiceFlow, INVOICE_STEP } from '../hooks/useInvoiceFlow.js';
import { useInvoiceHistory } from '../hooks/useInvoiceHistory.js';
import { InvoiceReviewStep } from '../components/vision/InvoiceReviewStep.jsx';
import { VisionDoneStep } from '../components/vision/VisionDoneStep.jsx';

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

  const { status: histStatus, data: histData, error: histError, refresh } = useInvoiceHistory();
  const [expandedKey, setExpandedKey] = useState(null);

  const { step, loading, error, result, items } = state;

  if (step === INVOICE_STEP.REVIEW) {
    return (
      <InvoiceReviewStep
        state={state}
        dispatch={dispatch}
        loading={loading}
        error={error}
        onConfirm={handleConfirm}
      />
    );
  }

  if (step === INVOICE_STEP.DONE) {
    const skipped = result ? items.length - result.items_processed : 0;
    return (
      <VisionDoneStep
        summary={`✅ ${result?.items_processed ?? 0} items added to inventory, ${skipped} skipped`}
        items={result?.items}
        renderItem={(it) => (
          <>
            <span
              className={[
                'rounded px-2 py-0.5 text-xs font-medium',
                it.action === 'matched' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700',
              ].join(' ')}
            >
              {it.action === 'matched' ? 'Existing' : 'New'}
            </span>
            {it.name} — {it.quantity} {it.unit}
          </>
        )}
        resetLabel="Scan Another Invoice"
        reset={() => { reset(); refresh(); }}
        navigate={navigate}
      />
    );
  }

  const toggleKey = (key) => setExpandedKey((prev) => (prev === key ? null : key));

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold">Invoice Scan</h1>

      <div
        className="flex items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white px-4 py-3 hover:border-brand transition-colors cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
        onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFileChange(f); }}
        onDragOver={(e) => e.preventDefault()}
      >
        {preview ? (
          <img src={preview} alt="preview" className="h-10 w-10 rounded object-cover shrink-0" />
        ) : (
          <span className="text-2xl shrink-0">📄</span>
        )}
        <p className="flex-1 truncate text-sm text-slate-600">
          {file ? file.name : 'Click or drag an invoice image'}
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
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-700">Invoice History</h2>
          {histData.invoices.length === 0 ? (
            <p className="text-sm text-slate-500">No invoices scanned yet.</p>
          ) : (
            <ul className="space-y-1">
              {histData.invoices.map((inv) => {
                const key = `${inv.supplier}|${inv.date}`;
                const isOpen = expandedKey === key;
                return (
                  <li key={key} className="overflow-hidden rounded-md border border-slate-100 bg-white text-sm">
                    <button
                      onClick={() => toggleKey(key)}
                      className="grid w-full grid-cols-[1fr_5rem_4.5rem_6rem] items-center gap-2 px-3 py-2 text-left hover:bg-slate-50 transition-colors"
                    >
                      <span className="truncate font-medium text-slate-700">{inv.supplier}</span>
                      <span className="text-xs text-slate-400">{inv.date}</span>
                      <span className="text-right text-xs text-slate-500">{inv.item_count} items</span>
                      <span className="flex items-center justify-end gap-1.5 font-medium">
                        {inv.total_cost != null ? `$${inv.total_cost.toFixed(2)}` : '—'}
                        <span className="text-xs text-slate-400">{isOpen ? '▲' : '▼'}</span>
                      </span>
                    </button>
                    {isOpen && (
                      <ul className="divide-y divide-slate-50 border-t border-slate-100">
                        {inv.items.map((item, idx) => (
                          <li
                            key={`${item.ingredient_name}-${idx}`}
                            className="grid grid-cols-[1fr_5rem_4.5rem_6rem] items-center gap-2 bg-slate-50 px-3 py-1.5 text-xs text-slate-600"
                          >
                            <span className="truncate pl-2">{item.ingredient_name}</span>
                            <span className="text-slate-400">{inv.date}</span>
                            <span className="text-right text-slate-500">{item.quantity} {item.unit}</span>
                            <span className="text-right font-medium">
                              {item.line_total != null ? `$${item.line_total.toFixed(2)}` : '—'}
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

export default Invoice;
