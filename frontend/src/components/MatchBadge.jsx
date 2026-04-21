/**
 * MatchBadge — displays a match status badge or a match-selection dropdown.
 *
 * Props:
 *   item            - the row item (must have include, match_score, suggested_match)
 *   idx             - row index forwarded to the dispatch onChange
 *   dispatch        - reducer dispatch from the parent page
 *   selectValue     - controlled value for the <select> (string)
 *   fallbackOption  - <option> label for the "no match / create" choice (e.g. "Create new" | "Skip")
 *   fallbackValue   - value for the fallback <option> (e.g. "__new__" | "__skip__")
 *   noMatchLabel    - text shown when match_score < 0.7 (e.g. "✨ New ingredient")
 *   noMatchClass    - Tailwind text-color class for the no-match span (default "text-slate-400")
 */
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

  if (item.match_score >= 0.7) {
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
