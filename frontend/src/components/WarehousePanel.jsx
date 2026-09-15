import { formatKm } from '../lib/format'
import InfoCard, { DataRow } from './InfoCard'
import StatusBadge from './StatusBadge'
import { WarehouseIcon } from './icons'

/** Warehouse Agent results: which warehouse was chosen and why. */
export default function WarehousePanel({ warehouse }) {
  return (
    <InfoCard
      title="Selected warehouse"
      icon={<WarehouseIcon className="h-3.5 w-3.5" />}
      action={<StatusBadge status={warehouse.status} />}
    >
      <div className="mb-3 flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="text-lg font-bold text-slate-900">{warehouse.id || '-'}</span>
        <span className="text-sm text-slate-500">{warehouse.location}</span>
      </div>

      <dl className="divide-y divide-slate-100">
        {warehouse.region && <DataRow label="Region">{warehouse.region}</DataRow>}
        <DataRow label="Distance from origin">
          {formatKm(warehouse.distance_from_origin_km)}
        </DataRow>
        <DataRow label="Item stocked here">
          {warehouse.item_in_stock_here ? (
            <span className="text-emerald-600">Yes</span>
          ) : (
            <span className="text-amber-600">No - transfer needed</span>
          )}
        </DataRow>
      </dl>

      {warehouse.message && (
        <p className="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {warehouse.message}
        </p>
      )}
    </InfoCard>
  )
}
