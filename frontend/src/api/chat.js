import { get, post, del } from './client';

export function sendMessage(sessionId, newUserMessage) {
  return post('/api/chat/message', {
    session_id: sessionId,
    messages: [{ role: 'user', content: newUserMessage }],
  });
}

export function fetchHistory(sessionId) {
  return get(`/api/chat/history/${sessionId}`);
}

export function clearHistory(sessionId) {
  return del(`/api/chat/history/${sessionId}`);
}
