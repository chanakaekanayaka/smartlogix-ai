/** Top application bar for the logistics dashboard. */
export default function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-gradient-to-r from-navy-950/90 via-navy-900/88 to-navy-800/85 shadow-[0_1px_0_0_rgba(255,255,255,0.04),0_8px_30px_-12px_rgba(0,0,0,0.5)] backdrop-blur-xl">
      <div className="h-[3px] w-full bg-gradient-to-r from-brand-500 via-brand-400 to-emerald-400" />

      <div className="mx-auto flex max-w-7xl items-center gap-3.5 px-4 py-3.5 sm:px-6">
        <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-emerald-500 text-white shadow-glow ring-1 ring-white/15">
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="currentColor" aria-hidden="true">
            <path d="M3 6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1h2.6a2 2 0 0 1 1.7.9l1.9 3a2 2 0 0 1 .3 1.1V17a1 1 0 0 1-1 1h-1.2a3 3 0 0 1-5.6 0H10a3 3 0 0 1-5.6 0H4a1 1 0 0 1-1-1V6Zm12 3h4.3l-1.6-2.5a.5.5 0 0 0-.4-.2H15v2.7ZM7.2 17a1 1 0 1 0 2 0 1 1 0 0 0-2 0Zm9 0a1 1 0 1 0 2 0 1 1 0 0 0-2 0Z" />
          </svg>
        </div>

        <div className="min-w-0 leading-tight">
          <h1 className="truncate text-lg font-extrabold tracking-tight text-white">SmartLogix</h1>
          <p className="truncate text-[11px] font-medium uppercase tracking-wider text-slate-400">
            AI Logistics Assistant
          </p>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-xs font-medium text-slate-300 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] sm:inline-flex">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]" />
            </span>
            Multi-agent pipeline live
          </span>
        </div>
      </div>
    </header>
  )
}
