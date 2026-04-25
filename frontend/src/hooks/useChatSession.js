import { useEffect, useRef, useState } from 'react';
import { sendMessage, fetchHistory, clearHistory } from '../api/chat.js';
import { STORAGE_KEY_CHAT_SESSION } from '../constants.js';

const GREETING = {
  role: 'assistant',
  content: "Hi! I'm your restaurant partner. Ask me anything about sales, stock, or orders.",
};

function getOrCreateSessionId() {
  let id = localStorage.getItem(STORAGE_KEY_CHAT_SESSION);
  if (!id) {
    id = typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem(STORAGE_KEY_CHAT_SESSION, id);
  }
  return id;
}

export function useChatSession() {
  const sessionId = useRef(getOrCreateSessionId());
  const [messages, setMessages] = useState([]);
  const [historyStatus, setHistoryStatus] = useState('loading');
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    fetchHistory(sessionId.current)
      .then((history) => {
        if (cancelled) return;
        setMessages(history.length > 0 ? history : [GREETING]);
        setHistoryStatus('ready');
      })
      .catch(() => {
        if (cancelled) return;
        setMessages([GREETING]);
        setHistoryStatus('ready');
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  async function handleSend(event) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setInput('');
    setIsSending(true);
    setError(null);

    try {
      const data = await sendMessage(sessionId.current, trimmed);
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
    } catch (err) {
      setError(err.message || 'Failed to reach the assistant.');
    } finally {
      setIsSending(false);
    }
  }

  async function handleClear() {
    try {
      await clearHistory(sessionId.current);
    } catch (err) {
      console.warn('clear history failed:', err);
    }
    setMessages([GREETING]);
    setShowClearConfirm(false);
    setError(null);
  }

  return {
    messages,
    historyStatus,
    input,
    setInput,
    isSending,
    error,
    showClearConfirm,
    setShowClearConfirm,
    bottomRef,
    handleSend,
    handleClear,
  };
}
