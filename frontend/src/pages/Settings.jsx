import { useEffect, useState } from 'react';

// Settings page: shows backend health and basic restaurant preferences.
function Settings() {
  const [health, setHealth] = useState('unknown');
  const [restaurantName, setRestaurantName] = useState(
    () => window.localStorage.getItem('restaurant_name') || ''
  );

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const response = await fetch('/api/../health').catch(() => fetch('/health'));
        if (response && response.ok) {
          const data = await response.json();
          if (!cancelled) setHealth(data.status || 'ok');
        } else if (!cancelled) {
          setHealth('unavailable');
        }
      } catch {
        if (!cancelled) setHealth('unavailable');
      }
    }

    checkHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleNameChange(event) {
    const value = event.target.value;
    setRestaurantName(value);
    window.localStorage.setItem('restaurant_name', value);
  }

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold">Settings</h1>
        <p className="text-sm text-slate-500">Basic configuration for your workspace.</p>
      </header>

      <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label htmlFor="restaurant-name" className="block text-sm font-medium text-slate-700">
          Restaurant name
        </label>
        <input
          id="restaurant-name"
          type="text"
          value={restaurantName}
          onChange={handleNameChange}
          placeholder="e.g. Maple Diner"
          className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-brand-accent focus:outline-none focus:ring-2 focus:ring-brand-accent/20"
        />
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-sm font-medium text-slate-700">Backend status</p>
        <p className="text-xs text-slate-500">Current health check result.</p>
        <p className="mt-2 text-sm font-medium text-slate-900">{health}</p>
      </div>
    </section>
  );
}

export default Settings;
