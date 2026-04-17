// Single chat message bubble. Styling shifts based on message role.
function ChatBubble({ role, content }) {
  const isUser = role === 'user';
  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={[
          'max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm leading-relaxed shadow-sm',
          isUser
            ? 'rounded-br-sm bg-brand-accent text-white'
            : 'rounded-bl-sm bg-white text-slate-800 ring-1 ring-slate-200',
        ].join(' ')}
      >
        {content}
      </div>
    </div>
  );
}

export default ChatBubble;
