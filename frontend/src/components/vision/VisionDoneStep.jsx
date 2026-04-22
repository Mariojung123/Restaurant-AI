export function VisionDoneStep({ summary, items, renderItem, resetLabel, reset, navigate }) {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Done</h1>
      <p className="text-lg">{summary}</p>
      <ul className="flex flex-col gap-2">
        {items?.map((it, i) => (
          <li key={i} className="flex items-center gap-2 text-sm">
            {renderItem(it)}
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
          {resetLabel}
        </button>
      </div>
    </div>
  );
}
