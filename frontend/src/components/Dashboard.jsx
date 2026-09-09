import InfoCard from './InfoCard'
import ExplanationPanel from './ExplanationPanel'
import InventoryPanel from './InventoryPanel'
import PipelineStatus from './PipelineStatus'
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
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          Some stages were degraded ({data.problem_stages.join(', ')}). The plan
          below is a best effort.
        </p>
      )}

      {data.input_sanitized?.length > 0 && (
        <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
          Your request was cleaned before processing ({data.input_sanitized.join(', ')}).
        </p>
      )}

      {data.is_approximate_estimate && data.estimate_warning && (
        <p className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <span aria-hidden="true">⚠️</span>
          <span>{data.estimate_warning}</span>
        </p>
      )}

      <SummaryGrid data={data} />

      {/* Details + map */}
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="space-y-4 lg:col-span-2">
          <InventoryPanel inventory={data.inventory} />
          <WarehousePanel warehouse={data.warehouse} />
        </div>

        <div className="space-y-4 lg:col-span-3">
          <InfoCard title="Shipment map" icon="🗺️" className="overflow-hidden">
            <div className="-mx-5 -mb-4">
              <RouteMap coordinates={data.coordinates} />
            </div>
          </InfoCard>
          <RoutePanel route={data.route} />
        </div>
      </div>

      <ExplanationPanel
        explanation={data.explanation}
        source={data.explanation_source}
        snippets={data.knowledge_snippets}
        fairnessNote={data.responsible_ai?.fairness_note}
      />
    </div>
  )
}
