import { humanise, statusTone } from '../lib/format'

/**
 * A small pill that colour-codes a status string
 * (green = good, amber = degraded, red = failed, grey = unknown).
 */
export default function StatusBadge({ status, label }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs
                  font-medium ring-1 ring-inset ${statusTone(status)}`}
    >
      {label ?? humanise(status)}
    </span>
  )
}
