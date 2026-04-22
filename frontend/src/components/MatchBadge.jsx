import { FUZZY_MATCH_THRESHOLD } from '../constants.js';

export function MatchBadge({
  item,
  idx,
  dispatch,
  selectValue,
  fallbackOption,
  fallbackValue,
  noMatchLabel,
  noMatchClass = 'text-slate-400',
}) {
  if (!item.include) return null;

  if (item.match_score === 1.0) {
    return <span className="text-xs text-green-600 font-medium">✓ Matched</span>;
  }

  if (item.match_score >= FUZZY_MATCH_THRESHOLD) {
    return (
      <select
        className="text-xs border rounded px-1 py-0.5 text-yellow-700 bg-yellow-50"
        value={selectValue}
        onChange={(e) => dispatch({ type: 'SET_MATCH', idx, value: e.target.value })}
      >
        {item.suggested_match && (
          <option value={String(item.suggested_match.id)}>
            {item.suggested_match.name}
          </option>
        )}
        <option value={fallbackValue}>{fallbackOption}</option>
      </select>
    );
  }

  return <span className={`text-xs ${noMatchClass} font-medium`}>{noMatchLabel}</span>;
}
