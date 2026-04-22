import { useCallback, useEffect, useRef, useState } from 'react';
import { getForecast } from '../api/inventory';
import { urgencyLevel, isUrgent } from '../utils/dashboardUtils';

const LEVEL_ORDER = { reorder: 0, urgent: 0, warning: 1, ok: 2, 'no-data': 3 };

export function useDashboardForecast() {
  const [forecast, setForecast] = useState([]);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const cancelRef = useRef(null);

  const loadForecast = useCallback(() => {
    if (cancelRef.current) cancelRef.current();
    let cancelled = false;
    cancelRef.current = () => { cancelled = true; };

    setStatus('loading');
    getForecast()
      .then((data) => { if (!cancelled) { setForecast(data); setStatus('ready'); } })
      .catch((err) => { if (!cancelled) { setError(err.message); setStatus('error'); } });
  }, []);

  useEffect(() => {
    loadForecast();
    return () => { if (cancelRef.current) cancelRef.current(); };
  }, [loadForecast]);

  const handleSelectItem = useCallback((item) => {
    setSelectedItem((prev) =>
      prev?.ingredient_id === item.ingredient_id ? null : item
    );
  }, []);

  const handleUpdate = useCallback(() => {
    setSelectedItem(null);
    loadForecast();
  }, [loadForecast]);

  const handleDelete = useCallback(() => {
    setSelectedItem(null);
    loadForecast();
  }, [loadForecast]);

  const reorderItems = forecast.filter(isUrgent);
  const otherItems = forecast
    .filter((i) => !isUrgent(i))
    .sort((a, b) => LEVEL_ORDER[urgencyLevel(a)] - LEVEL_ORDER[urgencyLevel(b)]);

  return {
    status,
    error,
    reorderItems,
    otherItems,
    selectedItem,
    handleSelectItem,
    handleUpdate,
    handleDelete,
    setSelectedItem,
  };
}
