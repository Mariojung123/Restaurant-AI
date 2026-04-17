import { useEffect, useState } from 'react';

// Dashboard page: shows depletion forecast fetched from /api/inventory/forecast.
function Dashboard() {
  const [forecast, setForecast] = useState([]);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadForecast() {
      try {
        const response = await fetch('/api/inventory/forecast');
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const data = await response.json();
        if (!cancelled) {
          setForecast(data);
          setStatus('ready');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setStatus('error');
        }
      }
    }

    loadForecast();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold">Inventory forecast</h1>
        <p className="text-sm text-slate-500">
          Projected depletion based on recent sales patterns.
        </p>
      </header>

      {status === 'loading' && <p className="text-sm text-slate-500">Loading...</p>}
      {status === 'error' && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}
      {status === 'ready' && forecast.length === 0 && (
        <p className="text-sm text-slate-500">No ingredients tracked yet.</p>
      )}

      <ul className="space-y-2">
        {forecast.map((item) => (
          <li
            key={item.ingredient_id}
            className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm"
          >
            <div>
              <p className="text-sm font-medium">{item.ingredient_name}</p>
              <p className="text-xs text-slate-500">
                Stock: {item.current_stock} | Daily use: {item.daily_consumption.toFixed(2)}
              </p>
            </div>
            <span
              className={[
                'rounded-full px-2 py-0.5 text-xs font-medium',
                item.needs_reorder
                  ? 'bg-red-100 text-red-700'
                  : 'bg-emerald-100 text-emerald-700',
              ].join(' ')}
            >
              {item.days_remaining != null ? `${item.days_remaining.toFixed(1)} days` : 'n/a'}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default Dashboard;
