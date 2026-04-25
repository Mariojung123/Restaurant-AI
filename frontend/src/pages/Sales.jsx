import { useState } from 'react';
import { useSalesHistory } from '../hooks/useSalesHistory';
import { SALES_PERIOD_OPTIONS } from '../constants';

function Sales() {
  const { status, error, data, periodDays, setPeriodDays } = useSalesHistory();
  const [expandedDate, setExpandedDate] = useState(null);

  const toggleDate = (date) => setExpandedDate((prev) => (prev === date ? null : date));

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">Sales History</h1>
        <div className="flex gap-1">
          {SALES_PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.days}
              onClick={() => setPeriodDays(opt.days)}
              className={[
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                periodDays === opt.days
                  ? 'bg-brand text-white'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
              ].join(' ')}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </header>

      {status === 'loading' && <p className="text-sm text-slate-500">Loading...</p>}
      {status === 'error' && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {status === 'ready' && data && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Total Revenue</p>
              <p className="mt-1 text-2xl font-semibold">${data.total_revenue.toFixed(2)}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Items Sold</p>
              <p className="mt-1 text-2xl font-semibold">{data.total_items_sold}</p>
            </div>
          </div>

          {data.menu_summaries.length === 0 ? (
            <p className="text-sm text-slate-500">No sales recorded in this period.</p>
          ) : (
            <>
              <div>
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-700">By Menu Item</h2>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                      <th className="pb-2 font-medium">Menu Item</th>
                      <th className="pb-2 text-right font-medium">Qty Sold</th>
                      <th className="pb-2 text-right font-medium">Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.menu_summaries.map((m) => (
                      <tr key={m.recipe_id} className="border-b border-slate-100">
                        <td className="py-2">{m.recipe_name}</td>
                        <td className="py-2 text-right">{m.quantity}</td>
                        <td className="py-2 text-right">${m.revenue.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div>
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-700">By Day</h2>
                <ul className="space-y-1">
                  {data.daily_summaries.map((d) => {
                    const isOpen = expandedDate === d.date;
                    return (
                      <li key={d.date} className="rounded-md border border-slate-100 bg-white text-sm overflow-hidden">
                        <button
                          onClick={() => toggleDate(d.date)}
                          className="grid w-full grid-cols-[1fr_5rem_5.5rem] items-center px-3 py-2 text-left hover:bg-slate-50 transition-colors"
                        >
                          <span className="text-slate-700">{d.date}</span>
                          <span className="text-right text-slate-500">{d.items_sold} sold</span>
                          <span className="flex items-center justify-end gap-1.5 font-medium">
                            ${d.revenue.toFixed(2)}
                            <span className="text-slate-400 text-xs">{isOpen ? '▲' : '▼'}</span>
                          </span>
                        </button>
                        {isOpen && (
                          <ul className="border-t border-slate-100 divide-y divide-slate-50">
                            {d.items.map((m) => (
                              <li key={m.recipe_id} className="grid grid-cols-[1fr_5rem_5.5rem] items-center px-3 py-1.5 text-xs text-slate-600 bg-slate-50">
                                <span className="pl-2">{m.recipe_name}</span>
                                <span className="text-right">{m.quantity} sold</span>
                                <span className="text-right font-medium">${m.revenue.toFixed(2)}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}

export default Sales;
