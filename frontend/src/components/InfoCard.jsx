/**
 * Generic dashboard card: a titled panel with an optional action (e.g. a
 * status badge) in the header and arbitrary children in the body.
 */
export default function InfoCard({ title, icon, action, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      <header className="card-header">
        {icon && <span className="text-base">{icon}</span>}
        <span className="flex-1">{title}</span>
        {action}
      </header>
      <div className="card-body">{children}</div>
    </section>
  )
}

/** A label / value row used inside InfoCard bodies. */
export function DataRow({ label, children }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5 text-sm">
      <dt className="shrink-0 text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-800">{children}</dd>
    </div>
  )
}
