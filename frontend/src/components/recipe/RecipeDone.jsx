function RecipeDone({ result, onBackToList, onAddAnother }) {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Done</h1>
      <p className="text-lg">
        Recipe saved — {result?.ingredients_linked ?? 0} ingredients linked,{' '}
        {result?.ingredients_created ?? 0} new ingredients created
      </p>
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <span className="font-medium">{result?.name}</span>
        {result?.price > 0 && (
          <span className="ml-2 text-slate-500">${parseFloat(result.price).toFixed(2)}</span>
        )}
      </div>
      <div className="flex gap-3">
        <button
          onClick={onBackToList}
          className="flex-1 border border-brand text-brand px-4 py-2 rounded-lg font-medium"
        >
          Back to List
        </button>
        <button
          onClick={onAddAnother}
          className="flex-1 bg-brand text-white px-4 py-2 rounded-lg font-medium"
        >
          Add Another Recipe
        </button>
      </div>
    </div>
  );
}

export default RecipeDone;
