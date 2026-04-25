import { useCallback, useEffect, useState } from 'react';
import { fetchReceiptHistory } from '../api/receipt.js';

export function useReceiptHistory() {
  const [status, setStatus] = useState('loading');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    setStatus('loading');
    fetchReceiptHistory()
      .then((d) => { if (!cancelled) { setData(d); setStatus('ready'); } })
      .catch((e) => { if (!cancelled) { setError(e.message); setStatus('error'); } });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => load(), [load]);

  return { status, data, error, refresh: load };
}
