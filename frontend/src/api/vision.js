const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function _postFile(path, file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${API}${path}`, { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? res.statusText);
  return data;
}

async function _postJson(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? res.statusText);
  return data;
}

export function previewInvoice(file) {
  return _postFile('/api/vision/invoice/preview', file);
}

export function confirmInvoice(payload) {
  return _postJson('/api/vision/invoice/confirm', payload);
}

export function previewReceipt(file) {
  return _postFile('/api/vision/receipt/preview', file);
}

export function confirmReceipt(payload) {
  return _postJson('/api/vision/receipt/confirm', payload);
}
