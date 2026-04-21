import { useReducer } from 'react';
import { useNavigate } from 'react-router-dom';
import { previewInvoice, confirmInvoice } from '../api/vision.js';
import { useVisionUpload } from './useVisionUpload.js';
import { FUZZY_MATCH_THRESHOLD } from '../constants';

export const INVOICE_STEP = { UPLOAD: 'upload', REVIEW: 'review', DONE: 'done' };

const initialState = {
  step: INVOICE_STEP.UPLOAD,
  items: [],
  supplier: '',
  invoiceDate: '',
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
        step: INVOICE_STEP.REVIEW,
        supplier: action.supplier,
        invoiceDate: action.invoiceDate,
        duplicateWarning: action.duplicateWarning,
        items: action.items,
      };
    case 'CONFIRM_START':
      return { ...state, loading: true, error: '' };
    case 'CONFIRM_SUCCESS':
      return { ...state, loading: false, step: INVOICE_STEP.DONE, result: action.result };
    case 'REQUEST_ERROR':
      return { ...state, loading: false, error: action.error };
    case 'SET_FIELD':
      return { ...state, [action.field]: action.value };
    case 'UPDATE_ITEM':
      return {
        ...state,
        items: state.items.map((it, i) =>
          i === action.idx ? { ...it, [action.field]: action.value } : it
        ),
      };
    case 'SET_MATCH':
      return {
        ...state,
        items: state.items.map((it, i) => {
          if (i !== action.idx) return it;
          return action.value === '__new__'
            ? { ...it, ingredient_id: null, _useNew: true }
            : { ...it, ingredient_id: parseInt(action.value, 10), _useNew: false };
        }),
      };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function useInvoiceFlow() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { file, preview, fileInputRef, handleFileChange, reset: resetUpload } = useVisionUpload();
  const navigate = useNavigate();

  async function handleAnalyze() {
    if (!file) return;
    dispatch({ type: 'ANALYZE_START' });
    try {
      const data = await previewInvoice(file);
      dispatch({
        type: 'ANALYZE_SUCCESS',
        supplier: data.supplier ?? '',
        invoiceDate: data.invoice_date ?? '',
        duplicateWarning: data.duplicate_warning,
        items: data.items.map((it) => ({
          ...it,
          include: true,
          ingredient_id: it.suggested_match?.id ?? null,
          _useNew: !it.suggested_match || it.match_score < FUZZY_MATCH_THRESHOLD,
        })),
      });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleConfirm() {
    dispatch({ type: 'CONFIRM_START' });
    try {
      const data = await confirmInvoice({
        supplier: state.supplier || null,
        invoice_date: state.invoiceDate || null,
        items: state.items.map((it) => ({
          name: it.name,
          quantity: parseFloat(it.quantity),
          unit: it.unit,
          unit_price: it.unit_price ? parseFloat(it.unit_price) : null,
          ingredient_id: it.include && !it._useNew ? it.ingredient_id : null,
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
