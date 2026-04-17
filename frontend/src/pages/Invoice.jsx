import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function Invoice() {
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [items, setItems] = useState([]);
  const [supplier, setSupplier] = useState('');
  const [invoiceDate, setInvoiceDate] = useState('');
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
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`${API}/api/vision/invoice/preview`, { method: 'POST', body: fd });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail ?? res.statusText);
      }
      const data = await res.json();
      setSupplier(data.supplier ?? '');
      setInvoiceDate(data.invoice_date ?? '');
      setDuplicateWarning(data.duplicate_warning);
      setItems(
        data.items.map((it) => ({
          ...it,
          include: true,
          ingredient_id: it.suggested_match?.id ?? null,
          _useNew: !it.suggested_match || it.match_score < 0.7,
        }))
      );
      setStep(2);
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
    if (value === '__new__') {
      updateItem(idx, 'ingredient_id', null);
      updateItem(idx, '_useNew', true);
    } else {
      const id = parseInt(value, 10);
      setItems((prev) =>
        prev.map((it, i) =>
          i === idx ? { ...it, ingredient_id: id, _useNew: false } : it
        )
      );
    }
  }

  async function handleConfirm() {
    setLoading(true);
    setError('');
    try {
      const payload = {
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
      };
      const res = await fetch(`${API}/api/vision/invoice/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail ?? res.statusText);
      }
      const data = await res.json();
      setResult(data);
      setStep(3);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setStep(1);
    setFile(null);
    setPreview(null);
    setItems([]);
    setSupplier('');
    setInvoiceDate('');
    setDuplicateWarning(false);
    setResult(null);
    setError('');
  }

  function matchBadge(item) {
    if (!item.include) return null;
    if (item.match_score === 1.0) {
      return <span className="text-xs text-green-600 font-medium">✓ Matched</span>;
    }
    if (item.match_score >= 0.7) {
      return (
        <select
          className="text-xs border rounded px-1 py-0.5 text-yellow-700 bg-yellow-50"
          value={item._useNew ? '__new__' : String(item.ingredient_id ?? '__new__')}
          onChange={(e) => handleMatchSelect(items.indexOf(item), e.target.value)}
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

  if (step === 1) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-xl font-semibold">Invoice Scan</h1>
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
              <span className="text-4xl">📄</span>
              <p className="text-slate-500 text-sm">Click or drag an image here</p>
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

  if (step === 2) {
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
              onChange={(e) => setSupplier(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1 flex-1">
            <label className="text-xs text-slate-500">Invoice Date</label>
            <input
              className="border rounded px-2 py-1 text-sm"
              value={invoiceDate}
              onChange={(e) => setInvoiceDate(e.target.value)}
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
                      className="border rounded px-1 py-0.5 w-16 text-xs"
                      value={item.quantity}
                      onChange={(e) => updateItem(idx, 'quantity', e.target.value)}
                    />
                  </td>
                  <td className="py-1.5 pr-2">
                    <input
                      className="border rounded px-1 py-0.5 w-14 text-xs"
                      value={item.unit}
                      onChange={(e) => updateItem(idx, 'unit', e.target.value)}
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
                  <td className="py-1.5">{matchBadge(item)}</td>
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

  const skipped = result
    ? items.length - result.items_processed
    : 0;

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
                it.action === 'matched'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-blue-100 text-blue-700',
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
