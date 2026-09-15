import InfoCard from './InfoCard'
import ExplanationPanel from './ExplanationPanel'
import { AlertTriangleIcon, MapIcon } from './icons'
import InventoryPanel from './InventoryPanel'
import PipelineStatus from './PipelineStatus'
import PricingPanel from './PricingPanel'
import RouteMap from './RouteMap'
import RoutePanel from './RoutePanel'
import SummaryGrid from './SummaryGrid'
import WarehousePanel from './WarehousePanel'

/**
 * The full results view. `data` is the backend's response object from
 * POST /api/delivery.
 */
export default function Dashboard({ data }) {
  return (
    <div className="space-y-4">
      <PipelineStatus
        pipelineStatus={data.pipeline_status}
        stageStatus={data.stage_status}
      />

      {data.problem_stages?.length > 0 && (
        <p className="flex items-start gap-2 rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-amber-100/50 px-3.5 py-2.5 text-xs text-amber-800 shadow-[inset_0_1px_0_rgba(255,255,255,0.5)]">
          <AlertTriangleIcon className="h-4 w-4 shrink-0 text-amber-600" />
          <span>
            Some stages were degraded ({data.problem_stages.join(', ')}). The plan
            below is a best effort.
          </span>
        </p>
      )}

      {data.input_sanitized?.length > 0 && (
        <p className="rounded-xl border border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100/50 px-3.5 py-2.5 text-xs text-slate-500">
          Your request was cleaned before processing ({data.input_sanitized.join(', ')}).
        </p>
      )}

      {data.is_approximate_estimate && data.estimate_warning && (
        <p className="flex gap-2 rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-amber-100/50 px-3.5 py-2.5 text-xs text-amber-800 shadow-[inset_0_1px_0_rgba(255,255,255,0.5)]">
          <AlertTriangleIcon className="h-4 w-4 shrink-0 text-amber-600" />
          <span>{data.estimate_warning}</span>
        </p>
      )}

      <SummaryGrid data={data} />

      {/* Details + map */}
      <div className="grid gap-4 md:grid-cols-5">
        <div className="space-y-4 md:col-span-2">
          <InventoryPanel inventory={data.inventory} />
          <WarehousePanel warehouse={data.warehouse} />
        </div>

        <div className="space-y-4 md:col-span-3">
          <InfoCard
            title="Shipment map"
            icon={<MapIcon className="h-3.5 w-3.5" />}
            className="overflow-hidden"
          >
            <div className="-mx-5 -mb-4">
              <RouteMap coordinates={data.coordinates} />
            </div>
          </InfoCard>
          <RoutePanel route={data.route} />
        </div>
      </div>

      <PricingPanel route={data.route} />

      <ExplanationPanel
        explanation={data.explanation}
        source={data.explanation_source}
        snippets={data.knowledge_snippets}
        fairnessNote={data.responsible_ai?.fairness_note}
      />
    </div>
  )
}
