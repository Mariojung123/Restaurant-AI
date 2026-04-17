import { useState } from 'react';
import ChatBubble from '../components/ChatBubble.jsx';

// Chat page: collects user text, posts to /api/chat/message, renders thread.
function Chat() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi! I'm your restaurant partner. Ask me anything about sales, stock, or orders.",
    },
  ]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);

  async function handleSend(event) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    const nextMessages = [...messages, { role: 'user', content: trimmed }];
    setMessages(nextMessages);
    setInput('');
    setIsSending(true);
    setError(null);

    try {
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: nextMessages }),
      });
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
    } catch (err) {
      setError(err.message || 'Failed to reach the assistant.');
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className="flex h-[calc(100vh-7rem)] flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto pb-4">
        {messages.map((m, idx) => (
          <ChatBubble key={idx} role={m.role} content={m.content} />
        ))}
        {isSending && <ChatBubble role="assistant" content="Typing..." />}
      </div>
      {error && (
        <p className="mb-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}
      <form onSubmit={handleSend} className="flex items-center gap-2 border-t border-slate-200 pt-3">
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about sales, inventory, orders..."
          className="flex-1 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm shadow-sm focus:border-brand-accent focus:outline-none focus:ring-2 focus:ring-brand-accent/20"
          disabled={isSending}
        />
        <button
          type="submit"
          disabled={isSending || !input.trim()}
          className="rounded-full bg-brand-accent px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Send
        </button>
      </form>
    </section>
  );
}

export default Chat;
