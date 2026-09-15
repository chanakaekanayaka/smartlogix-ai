import { formatLKR } from '../lib/format'
import InfoCard from './InfoCard'
import { CreditCardIcon, PackageIcon, ReceiptIcon, RulerIcon, ScaleIcon, TruckIcon } from './icons'

// Colour-coded by vehicle size/cost tier - lightest (motorbike) to heaviest (truck).
const VEHICLE_TIERS = {
  Motorbike: 'bg-sky-50 text-sky-700 ring-sky-600/20',
  'Three Wheeler': 'bg-teal-50 text-teal-700 ring-teal-600/20',
  Van: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20',
  Lorry: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  Truck: 'bg-rose-50 text-rose-700 ring-rose-600/20',
}
const DEFAULT_TIER = 'bg-slate-100 text-slate-700 ring-slate-600/20'

/** One line item in the cost-breakdown grid. */
function CostTile({ icon, label, value }) {
  if (value === null || value === undefined) return null
  return (
    <div className="rounded-xl border border-slate-200/70 bg-white/70 px-3 py-2.5 text-center shadow-sm">
      <div className="flex justify-center text-slate-400">{icon}</div>
      <div className="mt-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </div>
      <div className="mt-0.5 text-sm font-bold text-slate-900">{formatLKR(value)}</div>
    </div>
  )
}

/**
 * Dedicated pricing section for the results dashboard: the vehicle tier and
 * delivery mode as prominent badges, each cost component as its own tile,
 * and the total in a large highlighted banner.
 */
export default function PricingPanel({ route }) {
  const breakdown = route.cost_breakdown || {}
  const tierClass = VEHICLE_TIERS[route.vehicle] || DEFAULT_TIER

  return (
    <InfoCard
      title="Pricing & cost breakdown"
      icon={<CreditCardIcon className="h-3.5 w-3.5" />}
      action={
        route.delivery_mode && (
          <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700 ring-1 ring-inset ring-brand-600/20">
            {route.delivery_mode} delivery
          </span>
        )
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ring-1 ring-inset ${tierClass}`}
        >
          <TruckIcon className="h-3.5 w-3.5" />
          Vehicle tier: {route.vehicle || 'Unknown'}
        </span>
        {breakdown.mode_multiplier ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600 ring-1 ring-inset ring-slate-600/10">
            ×{breakdown.mode_multiplier} mode multiplier
          </span>
        ) : null}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        <CostTile icon={<ReceiptIcon className="h-5 w-5" />} label="Base rate" value={breakdown.base_fee} />
        <CostTile icon={<RulerIcon className="h-5 w-5" />} label="Distance" value={breakdown.distance_charge} />
        <CostTile icon={<ScaleIcon className="h-5 w-5" />} label="Weight" value={breakdown.weight_charge} />
        <CostTile icon={<PackageIcon className="h-5 w-5" />} label="Packaging" value={breakdown.packaging_cost} />
      </div>

      <div className="mt-4 flex flex-col items-start gap-1 rounded-2xl bg-gradient-to-r from-emerald-500 to-emerald-600 px-5 py-4 text-white shadow-[0_12px_28px_-10px_rgba(16,185,129,0.5)] sm:flex-row sm:items-center sm:justify-between">
        <span className="text-sm font-medium text-emerald-50">Total estimated cost</span>
        <span className="text-2xl font-extrabold tracking-tight">
          {formatLKR(route.estimated_cost_lkr ?? breakdown.total)}
        </span>
      </div>

      {route.is_approximate_estimate && (
        <p className="mt-3 text-[11px] leading-tight text-slate-400">
          Estimate calibrated against historical deliveries (~7% average error). Final charges are
          set at booking.
        </p>
      )}
    </InfoCard>
  )
}
