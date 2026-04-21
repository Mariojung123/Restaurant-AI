import { useRecipeFlow } from '../hooks/useRecipeFlow.js';
import { RECIPE_STEP, RECIPE_UNITS } from '../constants.js';
import RecipeList from '../components/recipe/RecipeList.jsx';
import RecipeDetail from '../components/recipe/RecipeDetail.jsx';
import RecipeForm from '../components/recipe/RecipeForm.jsx';
import RecipeDone from '../components/recipe/RecipeDone.jsx';

function Recipe() {
  const flow = useRecipeFlow();

  if (flow.step === RECIPE_STEP.DETAIL) {
    return (
      <RecipeDetail
        recipe={flow.selectedRecipe}
        detailStatus={flow.detailStatus}
        deleteConfirm={flow.deleteConfirm}
        loading={flow.loading}
        error={flow.error}
        onBack={flow.goToList}
        onEdit={flow.goToEdit}
        onSetDeleteConfirm={flow.setDeleteConfirm}
        onDelete={flow.handleDelete}
      />
    );
  }

  if (flow.step === RECIPE_STEP.EDIT) {
    return (
      <RecipeForm
        mode="edit"
        form={flow.form}
        ingredientRows={flow.ingredientRows}
        ingredients={flow.ingredients}
        units={RECIPE_UNITS}
        loading={flow.loading}
        error={flow.error}
        onBack={() => flow.goToDetail(flow.selectedRecipe)}
        onFormUpdate={flow.handleFormUpdate}
        onSave={flow.handleUpdate}
        onAddRow={flow.handleAddRow}
        onRemoveRow={flow.handleRemoveRow}
        onUpdateRow={flow.handleUpdateRow}
        onRowIngredientChange={flow.handleRowIngredientChange}
      />
    );
  }

  if (flow.step === RECIPE_STEP.LIST) {
    return (
      <RecipeList
        recipes={flow.recipes}
        listStatus={flow.listStatus}
        listError={flow.listError}
        onAddNew={flow.goToInput}
        onSelectRecipe={flow.handleSelectRecipe}
      />
    );
  }

  if (flow.step === RECIPE_STEP.INPUT) {
    return (
      <RecipeForm
        mode="input"
        form={flow.form}
        ingredientRows={flow.ingredientRows}
        ingredients={flow.ingredients}
        units={RECIPE_UNITS}
        loading={flow.loading}
        error={flow.error}
        onBack={flow.goToList}
        onFormUpdate={flow.handleFormUpdate}
        onSave={flow.handleSave}
        onAddRow={flow.handleAddRow}
        onRemoveRow={flow.handleRemoveRow}
        onUpdateRow={flow.handleUpdateRow}
        onRowIngredientChange={flow.handleRowIngredientChange}
      />
    );
  }

  return (
    <RecipeDone
      result={flow.result}
      onBackToList={flow.goToList}
      onAddAnother={flow.resetFlow}
    />
  );
}

export default Recipe;
