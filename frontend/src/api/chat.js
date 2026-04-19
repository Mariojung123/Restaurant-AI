import { post } from './client';

export function sendMessage(sessionId, messages) {
  return post('/api/chat/message', { session_id: sessionId, messages });
}
