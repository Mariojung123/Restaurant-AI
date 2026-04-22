import { useCallback } from 'react';
import { DASHBOARD_LOOKBACK_DAYS } from '../constants';
import { useDashboardForecast } from '../hooks/useDashboardForecast';
import ForecastCard from '../components/dashboard/ForecastCard';
import IngredientDetailPanel from '../components/dashboard/IngredientDetailPanel';

function Dashboard() {
  const {
    status,
    error,
    reorderItems,
    otherItems,
    selectedItem,
    handleSelectItem,
    handleUpdate,
    handleDelete,
    setSelectedItem,
  } = useDashboardForecast();

  const renderList = useCallback((items) => (
    <ul className="space-y-2">
      {items.map((item) => (
        <div key={item.ingredient_id} className="space-y-2">
          <ForecastCard
            item={item}
            isSelected={selectedItem?.ingredient_id === item.ingredient_id}
            onSelect={handleSelectItem}
          />
          {selectedItem?.ingredient_id === item.ingredient_id && (
            <IngredientDetailPanel
              item={item}
              onClose={() => setSelectedItem(null)}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
            />
          )}
        </div>
      ))}
    </ul>
  ), [selectedItem, handleSelectItem, setSelectedItem, handleUpdate, handleDelete]);

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold">Inventory forecast</h1>
        <p className="text-sm text-slate-500">
          Projected depletion based on last {DASHBOARD_LOOKBACK_DAYS} days of sales. Click an ingredient to see weekly usage.
        </p>
      </header>

      {status === 'loading' && <p className="text-sm text-slate-500">Loading...</p>}
      {status === 'error' && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}
      {status === 'ready' && reorderItems.length === 0 && otherItems.length === 0 && (
        <p className="text-sm text-slate-500">No ingredients tracked yet.</p>
      )}

      {status === 'ready' && reorderItems.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-red-600 uppercase tracking-wide">⚠ Needs attention</h2>
          {renderList(reorderItems)}
        </div>
      )}

      {status === 'ready' && otherItems.length > 0 && (
        <div className="space-y-2">
          {reorderItems.length > 0 && (
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">All ingredients</h2>
          )}
          {renderList(otherItems)}
        </div>
      )}
    </section>
  );
}

export default Dashboard;
