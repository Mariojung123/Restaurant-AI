import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { previewReceipt, confirmReceipt } from '../api/vision.js';

const STEP = { UPLOAD: 'upload', REVIEW: 'review', DONE: 'done' };

function Receipt() {
  const [step, setStep] = useState(STEP.UPLOAD);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [saleDate, setSaleDate] = useState('');
  const [items, setItems] = useState([]);
  const [duplicateWarning, setDuplicateWarning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  function handleFileChange(f) {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError('');
  }

  function handleDrop(e) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFileChange(f);
  }

  async function handleAnalyze() {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const data = await previewReceipt(file);
      setSaleDate(data.sale_date ?? '');
      setDuplicateWarning(data.duplicate_warning);
      setItems(
        data.items.map((it) => ({
          ...it,
          include: it.suggested_match !== null,
          recipe_id: it.suggested_match?.id ?? null,
          _pendingRecipeId: it.suggested_match?.id ?? null,
        }))
      );
      setStep(STEP.REVIEW);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function updateItem(idx, field, value) {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, [field]: value } : it)));
  }

  function handleMatchSelect(idx, value) {
    if (value === '__skip__') {
      setItems((prev) =>
        prev.map((it, i) => (i === idx ? { ...it, recipe_id: null, _pendingRecipeId: null } : it))
      );
    } else {
      const id = parseInt(value, 10);
      setItems((prev) =>
        prev.map((it, i) =>
          i === idx ? { ...it, recipe_id: id, _pendingRecipeId: id } : it
        )
      );
    }
  }

  async function handleConfirm() {
    setLoading(true);
    setError('');
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
      setResult(data);
      setStep(STEP.DONE);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setStep(STEP.UPLOAD);
    setFile(null);
    setPreview(null);
    setItems([]);
    setSaleDate('');
    setDuplicateWarning(false);
    setResult(null);
    setError('');
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
          value={item._pendingRecipeId !== null ? String(item._pendingRecipeId) : '__skip__'}
          onChange={(e) => handleMatchSelect(idx, e.target.value)}
        >
          {item.suggested_match && (
            <option value={String(item.suggested_match.id)}>
              {item.suggested_match.name}
            </option>
          )}
          <option value="__skip__">Skip</option>
        </select>
      );
    }
    return <span className="text-xs text-slate-400 font-medium">✨ No recipe — will skip</span>;
  }

  if (step === STEP.UPLOAD) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-xl font-semibold">Receipt Scan</h1>
        <div
          className="border-2 border-dashed border-slate-300 rounded-lg p-10 flex flex-col items-center gap-3 cursor-pointer hover:border-brand transition-colors"
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
        >
          {preview ? (
            <img src={preview} alt="preview" className="max-h-48 rounded" />
          ) : (
            <>
              <span className="text-4xl">🧾</span>
              <p className="text-slate-500 text-sm">Click or drag a receipt image here</p>
            </>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="hidden"
            onChange={(e) => e.target.files[0] && handleFileChange(e.target.files[0])}
          />
        </div>
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
            onChange={(e) => setSaleDate(e.target.value)}
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
                      onChange={(e) => updateItem(idx, 'include', e.target.checked)}
                    />
                  </td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-full text-xs"
                      value={item.name}
                      onChange={(e) => updateItem(idx, 'name', e.target.value)}
                    />
                  </td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-14 text-xs"
                      value={item.quantity}
                      onChange={(e) => updateItem(idx, 'quantity', e.target.value)}
                    />
                  </td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-16 text-xs"
                      value={item.unit_price ?? ''}
                      onChange={(e) => updateItem(idx, 'unit_price', e.target.value)}
                      placeholder="—"
                    />
                  </td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-16 text-xs"
                      value={item.total_price ?? ''}
                      onChange={(e) => updateItem(idx, 'total_price', e.target.value)}
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
