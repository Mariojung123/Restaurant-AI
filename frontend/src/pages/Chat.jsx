import { useChatSession } from '../hooks/useChatSession.js';
import ChatBubble from '../components/ChatBubble.jsx';

function Chat() {
  const {
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
  } = useChatSession();

  if (historyStatus === 'loading') {
    return (
      <section className="flex h-[calc(100vh-7rem)] items-center justify-center">
        <p className="text-sm text-slate-400">Loading conversation...</p>
      </section>
    );
  }

  return (
    <section className="flex h-[calc(100vh-7rem)] flex-col">
      <div className="flex items-center justify-end pb-2">
        {!showClearConfirm ? (
          <button
            onClick={() => setShowClearConfirm(true)}
            className="text-xs text-slate-400 hover:text-slate-600"
          >
            Clear conversation
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Clear all history?</span>
            <button
              onClick={() => setShowClearConfirm(false)}
              className="text-xs text-slate-500 border px-2 py-0.5 rounded"
            >
              Cancel
            </button>
            <button
              onClick={handleClear}
              className="text-xs text-white bg-red-500 px-2 py-0.5 rounded"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto pb-4">
        {messages.map((m, idx) => (
          <ChatBubble key={idx} role={m.role} content={m.content} />
        ))}
        {isSending && <ChatBubble role="assistant" content="Typing..." />}
        <div ref={bottomRef} />
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
          className="rounded-full bg-brand-accent px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-accent-dark disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Send
        </button>
      </form>
    </section>
  );
}

export default Chat;
