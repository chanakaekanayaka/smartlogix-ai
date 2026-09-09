import { humanise, statusTone } from '../lib/format'

const STAGE_LABELS = {
  query: 'Query',
  inventory: 'Inventory',
  warehouse: 'Warehouse',
  route: 'Route',
  retrieval: 'Explanation',
}

/**
 * Horizontal strip showing how each agent in the pipeline did.
 * `stageStatus` is the backend's `stage_status` object.
 */
export default function PipelineStatus({ pipelineStatus, stageStatus = {} }) {
  const stages = Object.keys(STAGE_LABELS).filter((key) => key in stageStatus)

  return (
    <div className="card">
      <div className="card-body flex flex-wrap items-center gap-x-2 gap-y-3">
        <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Pipeline
        </span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold
                      ring-1 ring-inset ${statusTone(pipelineStatus)}`}
        >
          {humanise(pipelineStatus)}
        </span>

        <div className="flex flex-1 flex-wrap items-center gap-1.5">
          {stages.map((stage, index) => (
            <div key={stage} className="flex items-center gap-1.5">
              {index > 0 && <span className="text-slate-300">→</span>}
              <span
                className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs
                            ring-1 ring-inset ${statusTone(stageStatus[stage])}`}
                title={`${STAGE_LABELS[stage]}: ${stageStatus[stage]}`}
              >
                {STAGE_LABELS[stage]}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
