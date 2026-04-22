import { useEffect, useState } from 'react';
import { getIngredientHistory, updateIngredient, deleteIngredient } from '../api/inventory';
import { DASHBOARD_LOOKBACK_OPTIONS } from '../constants';

export function useIngredientDetail(ingredientId, onUpdate, onDelete) {
  const [history, setHistory] = useState([]);
  const [historyStatus, setHistoryStatus] = useState('loading');
  const [lookbackDays, setLookbackDays] = useState(DASHBOARD_LOOKBACK_OPTIONS[0]);
  const [showEdit, setShowEdit] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setHistoryStatus('loading');
    getIngredientHistory(ingredientId, lookbackDays)
      .then((data) => { if (!cancelled) { setHistory(data); setHistoryStatus('ready'); } })
      .catch(() => { if (!cancelled) setHistoryStatus('error'); });
    return () => { cancelled = true; };
  }, [ingredientId, lookbackDays]);

  async function handleSave(stock, threshold, currentItem) {
    await updateIngredient(currentItem.ingredient_id, {
      current_stock: Number(stock),
      reorder_threshold: Number(threshold),
    });
    setShowEdit(false);
    onUpdate();
  }

  async function handleDelete(ingredientId) {
    await deleteIngredient(ingredientId);
    onDelete();
  }

  const maxAmount = Math.max(...history.map((r) => r.amount), 0.001);
  const hasData = history.some((r) => r.amount > 0);

  return {
    history,
    historyStatus,
    lookbackDays,
    setLookbackDays,
    showEdit,
    setShowEdit,
    showDeleteConfirm,
    setShowDeleteConfirm,
    maxAmount,
    hasData,
    handleSave,
    handleDelete,
  };
}
