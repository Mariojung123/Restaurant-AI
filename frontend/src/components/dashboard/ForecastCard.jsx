import { DASHBOARD_DAYS_PER_WEEK } from '../../constants';
import { urgencyLevel } from '../../utils/dashboardUtils';

export function formatStock(value, unit) {
  if (unit === 'g' && value >= 1000) return `${+((value / 1000).toFixed(3))}kg`;
  if (unit === 'mL' && value >= 1000) return `${+((value / 1000).toFixed(3))}L`;
  return `${+(value.toFixed(3))}${unit}`;
}

export function formatPurchaseDate(isoString) {
  if (!isoString) return 'No record';
  return new Date(isoString).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
}

function formatWeekly(dailyValue, unit) {
  return `${formatStock(dailyValue * DASHBOARD_DAYS_PER_WEEK, unit)}/week`;
}

const BORDER_COLOR = {
  reorder:   'border-red-300',
  urgent:    'border-red-300',
  warning:   'border-yellow-300',
  ok:        'border-slate-200',
  'no-data': 'border-slate-200',
};

const BADGE_STYLE = {
  reorder:   'bg-red-100 text-red-700',
  urgent:    'bg-red-100 text-red-700',
  warning:   'bg-yellow-100 text-yellow-700',
  ok:        'bg-emerald-100 text-emerald-700',
  'no-data': 'bg-slate-100 text-slate-500',
};

function StatusBadge({ item }) {
  const level = urgencyLevel(item);
  const label =
    level === 'no-data' ? 'No sales data'
    : level === 'reorder' ? 'Reorder now'
    : `${item.days_remaining.toFixed(1)} days left`;
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${BADGE_STYLE[level]}`}>
      {label}
    </span>
  );
}

function DepletionDate({ item }) {
  if (!item.depletion_date) return null;
  const formatted = new Date(item.depletion_date).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
  return <span className="text-xs text-slate-400">runs out {formatted}</span>;
}

export default function ForecastCard({ item, isSelected, onSelect }) {
  const level = urgencyLevel(item);
  return (
    <li
      className={`flex items-center justify-between rounded-lg border ${BORDER_COLOR[level]} bg-white px-4 py-3 shadow-sm cursor-pointer hover:bg-slate-50 transition-colors ${isSelected ? 'ring-2 ring-blue-300' : ''}`}
      onClick={onSelect}
    >
      <div className="space-y-0.5">
        <p className="text-sm font-medium">{item.ingredient_name}</p>
        <p className="text-xs text-slate-500">
          Stock: {formatStock(item.current_stock, item.unit)} | Weekly use: {formatWeekly(item.daily_consumption, item.unit)}
        </p>
        <DepletionDate item={item} />
      </div>
      <StatusBadge item={item} />
    </li>
  );
}
