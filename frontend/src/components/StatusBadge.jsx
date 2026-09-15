import { humanise, statusDot, statusTone } from '../lib/format'

/**
 * A small pill that colour-codes a status string
 * (green = good, amber = degraded, red = failed, grey = unknown).
 */
export default function StatusBadge({ status, label }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs
                  font-semibold ring-1 ring-inset ${statusTone(status)}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${statusDot(status)}`} />
      {label ?? humanise(status)}
    </span>
  )
}
