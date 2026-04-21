import { useEffect, useReducer } from 'react';
import { listRecipes, getRecipe, confirmRecipe, updateRecipe, deleteRecipe } from '../api/recipe.js';
import { listIngredients } from '../api/inventory.js';
import { RECIPE_STEP, RECIPE_EMPTY_FORM } from '../constants.js';

const emptyRow = () => ({ ingredientId: '', quantity: '', unit: 'g' });

const initialState = {
  step: RECIPE_STEP.LIST,
  recipes: [],
  listStatus: 'loading',
  listError: null,
  selectedRecipe: null,
  detailStatus: 'idle',
  deleteConfirm: false,
  form: RECIPE_EMPTY_FORM,
  ingredientRows: [emptyRow()],
  ingredients: [],
  loading: false,
  error: '',
  result: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'LIST_LOADING':
      return { ...state, listStatus: 'loading' };
    case 'LIST_SUCCESS':
      return { ...state, listStatus: 'ready', recipes: action.recipes };
    case 'LIST_ERROR':
      return { ...state, listStatus: 'error', listError: action.error };
    case 'GO_TO_INPUT':
      return { ...state, step: RECIPE_STEP.INPUT, error: '', form: RECIPE_EMPTY_FORM, ingredientRows: [emptyRow()] };
    case 'GO_TO_LIST':
      return { ...state, step: RECIPE_STEP.LIST, deleteConfirm: false };
    case 'GO_TO_DETAIL':
      return { ...state, step: RECIPE_STEP.DETAIL, selectedRecipe: action.recipe, detailStatus: 'ready', deleteConfirm: false, error: '' };
    case 'DETAIL_LOADING':
      return { ...state, detailStatus: 'loading' };
    case 'GO_TO_EDIT':
      return {
        ...state,
        step: RECIPE_STEP.EDIT,
        form: {
          name: state.selectedRecipe.name,
          price: String(state.selectedRecipe.price),
          description: state.selectedRecipe.description ?? '',
        },
        ingredientRows: state.selectedRecipe.ingredients.map((ing) => ({
          ingredientId: String(ing.ingredient_id),
          quantity: ing.quantity != null ? String(ing.quantity) : '',
          unit: ing.unit,
        })),
        error: '',
      };
    case 'SET_DELETE_CONFIRM':
      return { ...state, deleteConfirm: action.value };
    case 'FORM_UPDATE':
      return { ...state, form: { ...state.form, [action.field]: action.value } };
    case 'INGREDIENTS_LOADED':
      return { ...state, ingredients: action.ingredients };
    case 'ADD_ROW':
      return { ...state, ingredientRows: [...state.ingredientRows, emptyRow()] };
    case 'REMOVE_ROW':
      return { ...state, ingredientRows: state.ingredientRows.filter((_, i) => i !== action.idx) };
    case 'UPDATE_ROW': {
      const rows = state.ingredientRows.map((r, i) => {
        if (i !== action.idx) return r;
        const updated = { ...r, [action.field]: action.value };
        if (action.field === 'ingredientId' && action.autoUnit) {
          updated.unit = action.autoUnit;
        }
        return updated;
      });
      return { ...state, ingredientRows: rows };
    }
    case 'SAVE_START':
      return { ...state, loading: true, error: '' };
    case 'SAVE_SUCCESS':
      return { ...state, loading: false, step: RECIPE_STEP.DONE, result: action.result };
    case 'REQUEST_ERROR':
      return { ...state, loading: false, error: action.error };
    case 'RESET_FLOW':
      return { ...state, step: RECIPE_STEP.INPUT, form: RECIPE_EMPTY_FORM, ingredientRows: [emptyRow()], result: null, error: '' };
    default:
      return state;
  }
}

export function useRecipeFlow() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { step, ingredients } = state;

  useEffect(() => {
    if (step !== RECIPE_STEP.LIST) return;
    let cancelled = false;
    dispatch({ type: 'LIST_LOADING' });
    listRecipes()
      .then((data) => { if (!cancelled) dispatch({ type: 'LIST_SUCCESS', recipes: data }); })
      .catch((e) => { if (!cancelled) dispatch({ type: 'LIST_ERROR', error: e.message }); });
    return () => { cancelled = true; };
  }, [step]);

  useEffect(() => {
    if ((step !== RECIPE_STEP.INPUT && step !== RECIPE_STEP.EDIT) || ingredients.length > 0) return;
    listIngredients()
      .then((data) => dispatch({ type: 'INGREDIENTS_LOADED', ingredients: data }))
      .catch(() => {});
  }, [step, ingredients.length]);

  function buildItems(rows) {
    return rows
      .filter((r) => r.ingredientId && r.quantity)
      .map((r) => {
        const ing = ingredients.find((i) => i.id === parseInt(r.ingredientId, 10));
        return {
          name: ing.name,
          quantity: parseFloat(r.quantity),
          unit: r.unit,
          quantity_display: `${r.quantity}${r.unit}`,
          ingredient_id: ing.id,
          include: true,
        };
      });
  }

  async function handleSelectRecipe(recipeId) {
    dispatch({ type: 'DETAIL_LOADING' });
    try {
      const data = await getRecipe(recipeId);
      dispatch({ type: 'GO_TO_DETAIL', recipe: data });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleSave() {
    const items = buildItems(state.ingredientRows);
    if (items.length === 0) {
      dispatch({ type: 'REQUEST_ERROR', error: 'Add at least one ingredient with a quantity.' });
      return;
    }
    dispatch({ type: 'SAVE_START' });
    try {
      const data = await confirmRecipe({
        name: state.form.name.trim(),
        description: state.form.description.trim() || null,
        price: parseFloat(state.form.price) || 0,
        items,
      });
      dispatch({ type: 'SAVE_SUCCESS', result: data });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleUpdate() {
    dispatch({ type: 'SAVE_START' });
    try {
      const items = buildItems(state.ingredientRows);
      await updateRecipe(state.selectedRecipe.id, {
        name: state.form.name.trim(),
        description: state.form.description.trim() || null,
        price: parseFloat(state.form.price) || 0,
        items,
      });
      const detail = await getRecipe(state.selectedRecipe.id);
      dispatch({ type: 'GO_TO_DETAIL', recipe: detail });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  async function handleDelete() {
    dispatch({ type: 'SAVE_START' });
    try {
      await deleteRecipe(state.selectedRecipe.id);
      dispatch({ type: 'GO_TO_LIST' });
    } catch (e) {
      dispatch({ type: 'REQUEST_ERROR', error: e.message });
    }
  }

  function handleRowIngredientChange(idx, ingredientId) {
    const ing = ingredients.find((i) => i.id === parseInt(ingredientId, 10));
    dispatch({ type: 'UPDATE_ROW', idx, field: 'ingredientId', value: ingredientId, autoUnit: ing?.unit });
  }

  function handleFormUpdate(field, value) {
    dispatch({ type: 'FORM_UPDATE', field, value });
  }

  function handleAddRow() {
    dispatch({ type: 'ADD_ROW' });
  }

  function handleRemoveRow(idx) {
    dispatch({ type: 'REMOVE_ROW', idx });
  }

  function handleUpdateRow(idx, field, value) {
    dispatch({ type: 'UPDATE_ROW', idx, field, value });
  }

  return {
    ...state,
    goToInput: () => dispatch({ type: 'GO_TO_INPUT' }),
    goToList: () => dispatch({ type: 'GO_TO_LIST' }),
    goToEdit: () => dispatch({ type: 'GO_TO_EDIT' }),
    goToDetail: (recipe) => dispatch({ type: 'GO_TO_DETAIL', recipe }),
    setDeleteConfirm: (value) => dispatch({ type: 'SET_DELETE_CONFIRM', value }),
    resetFlow: () => dispatch({ type: 'RESET_FLOW' }),
    handleSelectRecipe,
    handleSave,
    handleUpdate,
    handleDelete,
    handleFormUpdate,
    handleAddRow,
    handleRemoveRow,
    handleUpdateRow,
    handleRowIngredientChange,
  };
}
