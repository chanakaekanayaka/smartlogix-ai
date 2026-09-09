import { formatDays, formatLKR } from '../lib/format'

/** One headline metric. */
function Stat({ label, value, sub, icon }) {
  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
          {icon && <span>{icon}</span>}
          {label}
        </div>
        <div className="mt-1 truncate text-lg font-semibold text-slate-900" title={String(value)}>
          {value || '-'}
        </div>
        {sub && <div className="mt-0.5 truncate text-xs text-slate-500">{sub}</div>}
      </div>
    </div>
  )
}

/**
 * The row of headline cards: route, item, cost and time.
 * `data` is the whole backend result object.
 */
export default function SummaryGrid({ data }) {
  const { request, route, inventory } = data

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Stat
        label="Route"
        icon="📍"
        value={`${request.origin || '?'} → ${request.destination || '?'}`}
        sub={route.distance_km ? `${Math.round(route.distance_km)} km by road` : 'distance unknown'}
      />
      <Stat
        label="Item"
        icon="📦"
        value={request.item || request.raw_item || '-'}
        sub={inventory.category || null}
      />
      <Stat
        label="Est. cost"
        icon="💰"
        value={formatLKR(route.estimated_cost_lkr)}
        sub={route.delivery_mode ? `${route.delivery_mode} delivery` : null}
      />
      <Stat
        label="Est. time"
        icon="⏱️"
        value={formatDays(route.estimated_days)}
        sub={route.vehicle ? `by ${route.vehicle}` : null}
      />
    </div>
  )
}
