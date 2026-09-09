/** Top application bar for the logistics dashboard. */
export default function Header() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 sm:px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
            <path d="M3 6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1h2.6a2 2 0 0 1 1.7.9l1.9 3a2 2 0 0 1 .3 1.1V17a1 1 0 0 1-1 1h-1.2a3 3 0 0 1-5.6 0H10a3 3 0 0 1-5.6 0H4a1 1 0 0 1-1-1V6Zm12 3h4.3l-1.6-2.5a.5.5 0 0 0-.4-.2H15v2.7ZM7.2 17a1 1 0 1 0 2 0 1 1 0 0 0-2 0Zm9 0a1 1 0 1 0 2 0 1 1 0 0 0-2 0Z" />
          </svg>
        </div>
        <div className="leading-tight">
          <h1 className="text-base font-bold text-slate-900">SmartLogix</h1>
          <p className="text-xs text-slate-500">AI Logistics Assistant</p>
        </div>
        <span className="ml-auto hidden rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500 sm:inline">
          Multi-agent pipeline
        </span>
      </div>
    </header>
  )
}
