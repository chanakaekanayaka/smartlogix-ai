import InfoCard, { DataRow } from './InfoCard'
import StatusBadge from './StatusBadge'
import { ArchiveIcon } from './icons'

/** Inventory Agent results: stock status, quantity, product attributes. */
export default function InventoryPanel({ inventory }) {
  return (
    <InfoCard
      title="Inventory"
      icon={<ArchiveIcon className="h-3.5 w-3.5" />}
      action={<StatusBadge status={inventory.status} />}
    >
      <dl className="divide-y divide-slate-100">
        <DataRow label="Available quantity">
          {inventory.available_quantity ?? 0} units
        </DataRow>
        {inventory.product_id && <DataRow label="Product ID">{inventory.product_id}</DataRow>}
        {inventory.category && <DataRow label="Category">{inventory.category}</DataRow>}
        {inventory.unit_weight_kg ? (
          <DataRow label="Unit weight">{inventory.unit_weight_kg} kg</DataRow>
        ) : null}
        <DataRow label="Handling">
          <span className="flex flex-wrap justify-end gap-1">
            {inventory.fragile && <Tag tone="amber">Fragile</Tag>}
            {inventory.requires_cold_storage && <Tag tone="sky">Cold storage</Tag>}
            {!inventory.fragile && !inventory.requires_cold_storage && (
              <span className="text-slate-400">Standard</span>
            )}
          </span>
        </DataRow>
      </dl>

      {inventory.message && (
        <p className="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {inventory.message}
        </p>
      )}
    </InfoCard>
  )
}

const TAG_TONES = {
  amber: 'bg-amber-50 text-amber-700',
  sky: 'bg-sky-50 text-sky-700',
}

function Tag({ tone = 'amber', children }) {
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${TAG_TONES[tone]}`}>
      {children}
    </span>
  )
}
