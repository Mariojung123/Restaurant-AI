import { useCallback, useEffect, useState } from 'react';
import { fetchInvoiceHistory } from '../api/invoice.js';

export function useInvoiceHistory() {
  const [status, setStatus] = useState('loading');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    setStatus('loading');
    fetchInvoiceHistory()
      .then((d) => { if (!cancelled) { setData(d); setStatus('ready'); } })
      .catch((e) => { if (!cancelled) { setError(e.message); setStatus('error'); } });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => load(), [load]);

  return { status, data, error, refresh: load };
}
