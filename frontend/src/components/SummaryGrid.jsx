import { formatDays, formatLKR } from '../lib/format'
import { ClockIcon, MapPinIcon, PackageIcon, WalletIcon } from './icons'

const TONES = {
  brand: {
    badge: 'bg-gradient-to-br from-brand-50 to-brand-100/60 text-brand-600 ring-1 ring-brand-600/10',
    glow: 'hover:shadow-[0_16px_32px_-12px_rgba(79,70,229,0.35)] hover:border-brand-200',
  },
  emerald: {
    badge: 'bg-gradient-to-br from-emerald-50 to-emerald-100/60 text-emerald-600 ring-1 ring-emerald-600/10',
    glow: 'hover:shadow-[0_16px_32px_-12px_rgba(16,185,129,0.35)] hover:border-emerald-200',
  },
  amber: {
    badge: 'bg-gradient-to-br from-amber-50 to-amber-100/60 text-amber-600 ring-1 ring-amber-600/10',
    glow: 'hover:shadow-[0_16px_32px_-12px_rgba(245,158,11,0.35)] hover:border-amber-200',
  },
  slate: {
    badge: 'bg-gradient-to-br from-slate-100 to-slate-200/60 text-slate-600 ring-1 ring-slate-600/10',
    glow: 'hover:shadow-elevated',
  },
}

/** One headline metric. */
function Stat({ label, value, sub, icon, tone = 'slate' }) {
  return (
    <div className={`card transition duration-200 ease-out hover:-translate-y-0.5 ${TONES[tone].glow}`}>
      <div className="card-body flex items-start gap-3 sm:px-5 sm:py-4">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${TONES[tone].badge}`}>
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</div>
          <div className="mt-0.5 truncate text-lg font-bold text-slate-900 sm:text-xl" title={String(value)}>
            {value || '-'}
          </div>
          {sub && <div className="mt-0.5 truncate text-xs text-slate-500">{sub}</div>}
        </div>
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
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
      <Stat
        label="Route"
        icon={<MapPinIcon className="h-5 w-5" />}
        tone="brand"
        value={`${request.origin || '?'} → ${request.destination || '?'}`}
        sub={route.distance_km ? `${Math.round(route.distance_km)} km by road` : 'distance unknown'}
      />
      <Stat
        label="Item"
        icon={<PackageIcon className="h-5 w-5" />}
        tone="slate"
        value={request.item || request.raw_item || '-'}
        sub={inventory.category || null}
      />
      <Stat
        label="Est. cost"
        icon={<WalletIcon className="h-5 w-5" />}
        tone="emerald"
        value={formatLKR(route.estimated_cost_lkr)}
        sub={route.delivery_mode ? `${route.delivery_mode} delivery` : null}
      />
      <Stat
        label="Est. time"
        icon={<ClockIcon className="h-5 w-5" />}
        tone="amber"
        value={formatDays(route.estimated_days)}
        sub={route.vehicle ? `by ${route.vehicle}` : null}
      />
    </div>
  )
}
