import { useReducer } from 'react';
import { useNavigate } from 'react-router-dom';
import { previewReceipt, confirmReceipt } from '../api/vision.js';
import { useVisionUpload } from './useVisionUpload.js';

export const RECEIPT_STEP = { UPLOAD: 'upload', REVIEW: 'review', DONE: 'done' };

const initialState = {
  step: RECEIPT_STEP.UPLOAD,
  saleDate: '',
  items: [],
  duplicateWarning: false,
  loading: false,
  result: null,
  error: '',
};

function reducer(state, action) {
  switch (action.type) {
    case 'ANALYZE_START':
      return { ...state, loading: true, error: '' };
    case 'ANALYZE_SUCCESS':
      return {
        ...state,
        loading: false,
        step: RECEIPT_STEP.REVIEW,
        saleDate: action.saleDate,
        duplicateWarning: action.duplicateWarning,
        items: action.items,
      };
    case 'CONFIRM_START':
      return { ...state, loading: true, error: '' };
    case 'CONFIRM_SUCCESS':
      return { ...state, loading: false, step: RECEIPT_STEP.DONE, result: action.result };
    case 'REQUEST_ERROR':
      return { ...state, loading: false, error: action.error };
    case 'SET_SALE_DATE':
      return { ...state, saleDate: action.value };
    case 'UPDATE_ITEM': {
      const updated = state.items.map((it, i) => {
        if (i !== action.idx) return it;
        const next = { ...it, [action.field]: action.value };
        if (action.field === 'quantity' || action.field === 'unit_price') {
          const qty = parseFloat(action.field === 'quantity' ? action.value : it.quantity);
          const price = parseFloat(action.field === 'unit_price' ? action.value : it.unit_price);
          if (!isNaN(qty) && !isNaN(price)) next.total_price = String(+(qty * price).toFixed(2));
        }
        return next;
      });
      return { ...state, items: updated };
    }
    case 'SET_MATCH':
      return {
        ...state,
        items: state.items.map((it, i) => {
          if (i !== action.idx) return it;
          return action.value === '__skip__'
            ? { ...it, recipe_id: null, _pendingRecipeId: null }
            : { ...it, recipe_id: parseInt(action.value, 10), _pendingRecipeId: parseInt(action.value, 10) };
        }),
      };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function useReceiptFlow() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { file, preview, fileInputRef, handleFileChange, reset: resetUpload } = useVisionUpload();
  const navigate = useNavigate();

  async function handleAnalyze() {
    if (!file) return;
    dispatch({ type: 'ANALYZE_START' });
    try {
      const data = await previewReceipt(file);
      dispatch({
        type: 'ANALYZE_SUCCESS',
        saleDate: data.sale_date ?? '',
        duplicateWarning: data.duplicate_warning,
        items: data.items.map((it) => ({
          ...it,
          include: it.suggested_match !== null,
          recipe_id: it.suggested_match?.id ?? null,
          _pendingRecipeId: it.suggested_match?.id ?? null,
        })),
      });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleConfirm() {
    dispatch({ type: 'CONFIRM_START' });
    try {
      const data = await confirmReceipt({
        sale_date: state.saleDate || null,
        items: state.items.map((it) => ({
          name: it.name,
          quantity: parseInt(it.quantity, 10),
          unit_price: it.unit_price ? parseFloat(it.unit_price) : null,
          total_price: it.total_price ? parseFloat(it.total_price) : null,
          recipe_id: it.include ? it.recipe_id : null,
          include: it.include,
        })),
      });
      dispatch({ type: 'CONFIRM_SUCCESS', result: data });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  function reset() {
    resetUpload();
    dispatch({ type: 'RESET' });
  }

  return {
    state,
    dispatch,
    file,
    preview,
    fileInputRef,
    handleFileChange,
    handleAnalyze,
    handleConfirm,
    reset,
    navigate,
  };
}
