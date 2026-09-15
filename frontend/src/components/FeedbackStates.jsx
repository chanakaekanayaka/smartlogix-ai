import { AlertTriangleIcon, ChevronRightIcon, InboxIcon } from './icons'

const LOADING_STAGES = ['Query', 'Inventory', 'Warehouse', 'Route', 'Explanation']

/** Placeholder shown before the first search. */
export function EmptyState() {
  return (
    <div className="card">
      <div className="card-body flex flex-col items-center gap-3 py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-50 to-emerald-50 text-brand-600 shadow-[0_8px_24px_-8px_rgba(79,70,229,0.25)] ring-1 ring-slate-900/5">
          <InboxIcon className="h-6 w-6" />
        </div>
        <p className="text-sm font-semibold text-slate-700">No delivery planned yet</p>
        <p className="max-w-sm text-sm text-slate-500">
          Enter a request above - the agents will parse it, check stock, pick a
          warehouse, choose a vehicle, estimate the cost and explain the plan.
        </p>
      </div>
    </div>
  )
}

/** Full-width skeleton while the pipeline runs - mirrors the real dashboard shape. */
export function LoadingState() {
  return (
    <div className="card">
      <div className="card-body space-y-5 py-10">
        <div className="mx-auto flex max-w-sm flex-col items-center gap-3 text-center">
          <svg className="h-8 w-8 animate-spin text-brand-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" />
          </svg>
          <p className="text-sm font-medium text-slate-700">Running the agent pipeline...</p>
          <div className="flex flex-wrap items-center justify-center gap-1.5">
            {LOADING_STAGES.map((stage, index) => (
              <div key={stage} className="flex items-center gap-1.5">
                {index > 0 && <ChevronRightIcon className="h-3 w-3 text-slate-300" />}
                <span
                  className="animate-pulse rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-400 ring-1 ring-slate-200"
                  style={{ animationDelay: `${index * 150}ms` }}
                >
                  {stage}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-xl bg-slate-100"
              style={{ animationDelay: `${i * 100}ms` }}
            />
          ))}
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="h-40 animate-pulse rounded-xl bg-slate-100" />
          <div className="h-40 animate-pulse rounded-xl bg-slate-100" />
        </div>
      </div>
    </div>
  )
}

/** Error banner with a retry button. */
export function ErrorState({ message, onRetry }) {
  return (
    <div className="card border-rose-200 ring-rose-900/5">
      <div className="card-body flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-50 text-rose-600">
          <AlertTriangleIcon className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-rose-800">Could not complete the request</p>
          <p className="text-sm text-rose-700">{message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="shrink-0 rounded-xl border border-rose-300 bg-white px-3.5 py-2 text-sm
                       font-semibold text-rose-700 transition hover:bg-rose-50"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  )
}
