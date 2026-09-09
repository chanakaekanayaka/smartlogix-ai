/** Placeholder shown before the first search. */
export function EmptyState() {
  return (
    <div className="card">
      <div className="card-body flex flex-col items-center gap-2 py-14 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-2xl">
          📦
        </div>
        <p className="text-sm font-medium text-slate-700">No delivery planned yet</p>
        <p className="max-w-sm text-sm text-slate-500">
          Enter a request above - the agents will parse it, check stock, pick a
          warehouse, choose a vehicle, estimate the cost and explain the plan.
        </p>
      </div>
    </div>
  )
}

/** Full-width skeleton while the pipeline runs. */
export function LoadingState() {
  return (
    <div className="card">
      <div className="card-body space-y-4 py-10">
        <div className="mx-auto flex max-w-sm flex-col items-center gap-3 text-center">
          <svg className="h-8 w-8 animate-spin text-brand-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" />
          </svg>
          <p className="text-sm font-medium text-slate-700">Running the agent pipeline...</p>
          <p className="text-xs text-slate-500">
            Query → Inventory → Warehouse → Route → Explanation
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg bg-slate-100" />
          ))}
        </div>
      </div>
    </div>
  )
}

/** Error banner with a retry button. */
export function ErrorState({ message, onRetry }) {
  return (
    <div className="card border-rose-200">
      <div className="card-body flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-rose-50 text-rose-600">
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
            <path d="M12 2 1 21h22L12 2Zm0 6c.6 0 1 .4 1 1v5a1 1 0 1 1-2 0V9c0-.6.4-1 1-1Zm0 9a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-rose-800">Could not complete the request</p>
          <p className="text-sm text-rose-700">{message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="shrink-0 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-sm
                       font-medium text-rose-700 transition hover:bg-rose-50"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  )
}
