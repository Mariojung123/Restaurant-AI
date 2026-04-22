import { useReceiptFlow, RECEIPT_STEP } from '../hooks/useReceiptFlow.js';
import { VisionUploadStep } from '../components/vision/VisionUploadStep.jsx';
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

  const { step, loading, error, result } = state;

  if (step === RECEIPT_STEP.UPLOAD) {
    return (
      <VisionUploadStep
        title="Receipt Scan"
        icon="🧾"
        hint="Click or drag a receipt image here"
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
      reset={reset}
      navigate={navigate}
    />
  );
}

export default Receipt;
