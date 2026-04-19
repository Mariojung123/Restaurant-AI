const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function _parse(res) {
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? res.statusText);
  return data;
}

export function get(path) {
  return fetch(`${BASE}${path}`).then(_parse);
}

export function post(path, body) {
  return fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(_parse);
}

export function postFile(path, file) {
  const fd = new FormData();
  fd.append('file', file);
  return fetch(`${BASE}${path}`, { method: 'POST', body: fd }).then(_parse);
}
