import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchSalesSummary } from '../api/sales';
import { SALES_DEFAULT_PERIOD_DAYS } from '../constants';

export function useSalesHistory() {
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [periodDays, setPeriodDays] = useState(SALES_DEFAULT_PERIOD_DAYS);
  const cancelRef = useRef(null);

  const load = useCallback(() => {
    if (cancelRef.current) cancelRef.current();
    let cancelled = false;
    cancelRef.current = () => { cancelled = true; };

    setStatus('loading');
    fetchSalesSummary(periodDays)
      .then((res) => { if (!cancelled) { setData(res); setStatus('ready'); } })
      .catch((err) => { if (!cancelled) { setError(err.message); setStatus('error'); } });
  }, [periodDays]);

  useEffect(() => {
    load();
    return () => { if (cancelRef.current) cancelRef.current(); };
  }, [load]);

  return { status, error, data, periodDays, setPeriodDays };
}
