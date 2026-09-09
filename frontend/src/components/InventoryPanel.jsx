import InfoCard, { DataRow } from './InfoCard'
import StatusBadge from './StatusBadge'

/** Inventory Agent results: stock status, quantity, product attributes. */
export default function InventoryPanel({ inventory }) {
  return (
    <InfoCard
      title="Inventory"
      icon="🗃️"
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
            {inventory.fragile && <Tag>Fragile</Tag>}
            {inventory.requires_cold_storage && <Tag>Cold storage</Tag>}
            {!inventory.fragile && !inventory.requires_cold_storage && (
              <span className="text-slate-400">Standard</span>
            )}
          </span>
        </DataRow>
      </dl>

      {inventory.message && (
        <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {inventory.message}
        </p>
      )}
    </InfoCard>
  )
}

function Tag({ children }) {
  return (
    <span className="rounded bg-amber-50 px-1.5 py-0.5 text-xs font-medium text-amber-700">
      {children}
    </span>
  )
}
