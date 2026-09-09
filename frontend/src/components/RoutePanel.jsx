import { formatDays, formatKm, formatLKR } from '../lib/format'
import InfoCard, { DataRow } from './InfoCard'
import StatusBadge from './StatusBadge'

/** Route Optimizer results: vehicle, mode, distance, time and cost breakdown. */
export default function RoutePanel({ route }) {
  const breakdown = route.cost_breakdown || {}

  return (
    <InfoCard title="Route & vehicle" icon="🚚" action={<StatusBadge status={route.status} />}>
      <dl className="divide-y divide-slate-100">
        <DataRow label="Vehicle">{route.vehicle || '-'}</DataRow>
        <DataRow label="Delivery mode">{route.delivery_mode || '-'}</DataRow>
        <DataRow label="Route distance">{formatKm(route.distance_km)}</DataRow>
        <DataRow label="Estimated time">{formatDays(route.estimated_days)}</DataRow>
      </dl>

      {/* Cost breakdown */}
      <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
        <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Cost estimate
        </p>
        <dl className="space-y-1 text-sm">
          <CostRow label="Base fee" value={breakdown.base_fee} />
          <CostRow label="Distance charge" value={breakdown.distance_charge} />
          <CostRow label="Weight charge" value={breakdown.weight_charge} />
          <CostRow label="Packaging" value={breakdown.packaging_cost} />
          {breakdown.mode_multiplier ? (
            <div className="flex justify-between text-xs text-slate-500">
              <dt>Mode multiplier</dt>
              <dd>×{breakdown.mode_multiplier}</dd>
            </div>
          ) : null}
          <div className="mt-1 flex justify-between border-t border-slate-200 pt-1.5 font-semibold text-slate-900">
            <dt>Total</dt>
            <dd>{formatLKR(route.estimated_cost_lkr ?? breakdown.total)}</dd>
          </div>
        </dl>
        {route.is_approximate_estimate && (
          <p className="mt-2 text-[11px] leading-tight text-slate-400">
            Estimate calibrated against historical deliveries (~7% average error).
          </p>
        )}
      </div>

      {route.message && (
        <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {route.message}
        </p>
      )}
    </InfoCard>
  )
}

function CostRow({ label, value }) {
  if (value === null || value === undefined) return null
  return (
    <div className="flex justify-between text-slate-600">
      <dt>{label}</dt>
      <dd>{formatLKR(value)}</dd>
    </div>
  )
}
