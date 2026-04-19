const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export async function sendMessage(sessionId, messages) {
  const res = await fetch(`${API}/api/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, messages }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? res.statusText);
  return data;
}
