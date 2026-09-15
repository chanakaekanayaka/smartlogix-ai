import { formatDays, formatKm } from '../lib/format'
import InfoCard, { DataRow } from './InfoCard'
import StatusBadge from './StatusBadge'
import { TruckIcon } from './icons'

/**
 * Route Optimizer results: vehicle, mode, distance and time.
 * The full cost breakdown lives in its own dedicated `PricingPanel`.
 */
export default function RoutePanel({ route }) {
  return (
    <InfoCard
      title="Route & vehicle"
      icon={<TruckIcon className="h-3.5 w-3.5" />}
      action={<StatusBadge status={route.status} />}
    >
      <dl className="divide-y divide-slate-100">
        <DataRow label="Vehicle">{route.vehicle || '-'}</DataRow>
        <DataRow label="Delivery mode">{route.delivery_mode || '-'}</DataRow>
        <DataRow label="Route distance">{formatKm(route.distance_km)}</DataRow>
        <DataRow label="Estimated time">{formatDays(route.estimated_days)}</DataRow>
      </dl>

      {route.message && (
        <p className="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {route.message}
        </p>
      )}
    </InfoCard>
  )
}
