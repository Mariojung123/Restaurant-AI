import { useState } from 'react';
import { STORAGE_KEY_RESTAURANT_NAME } from '../constants';

function Settings() {
  const [restaurantName, setRestaurantName] = useState(
    () => window.localStorage.getItem(STORAGE_KEY_RESTAURANT_NAME) || ''
  );

  function handleNameChange(event) {
    const value = event.target.value;
    setRestaurantName(value);
    window.localStorage.setItem(STORAGE_KEY_RESTAURANT_NAME, value);
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

    </section>
  );
}

export default Settings;
