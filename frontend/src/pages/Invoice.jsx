import { useInvoiceFlow, INVOICE_STEP } from '../hooks/useInvoiceFlow.js';
import { VisionUploadStep } from '../components/vision/VisionUploadStep.jsx';
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

  const { step, loading, error, result, items } = state;

  if (step === INVOICE_STEP.UPLOAD) {
    return (
      <VisionUploadStep
        title="Invoice Scan"
        icon="📄"
        hint="Click or drag an image here"
        preview={preview}
        fileInputRef={fileInputRef}
        onFile={handleFileChange}
        file={file}
        loading={loading}
        error={error}
        onAnalyze={handleAnalyze}
      />
    );
  }

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
      reset={reset}
      navigate={navigate}
    />
  );
}

export default Invoice;
