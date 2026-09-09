import { useState } from 'react'
import InfoCard from './InfoCard'
import StatusBadge from './StatusBadge'

/**
 * Responsible-AI panel: the Retrieval Agent's plain-English explanation of
 * *why* this warehouse / route / cost were chosen, how it was produced
 * (LLM vs rule-based), the exact policy snippets it was grounded in, and the
 * fairness note.
 */
export default function ExplanationPanel({ explanation, source, snippets = [], fairnessNote }) {
  const [showSources, setShowSources] = useState(false)

  return (
    <InfoCard
      title="Responsible AI explanation"
      icon="💡"
      action={
        <StatusBadge
          status={source}
          label={source === 'llm' ? 'AI generated' : 'Rule-based'}
        />
      }
    >
      <p className="text-sm leading-relaxed text-slate-700">
        {explanation || 'No explanation was produced.'}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
        <span>
          Grounded in {snippets.length} SmartLogix{' '}
          {snippets.length === 1 ? 'policy' : 'policies'} - no figures are invented.
        </span>
        {snippets.length > 0 && (
          <button
            type="button"
            onClick={() => setShowSources((v) => !v)}
            className="font-medium text-brand-600 hover:text-brand-700"
          >
            {showSources ? 'Hide sources' : 'Show sources'}
          </button>
        )}
      </div>

      {showSources && snippets.length > 0 && (
        <ul className="mt-2 space-y-2">
          {snippets.map((snippet, index) => (
            <li
              key={index}
              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"
            >
              <div className="mb-0.5 flex items-center justify-between gap-2">
                {snippet.section && (
                  <span className="font-semibold text-slate-500">{snippet.section}</span>
                )}
                {typeof snippet.score === 'number' && (
                  <span className="shrink-0 text-slate-400">
                    match {(1 - snippet.score).toFixed(2)}
                  </span>
                )}
              </div>
              <p className="text-slate-600">{snippet.text}</p>
            </li>
          ))}
        </ul>
      )}

      {fairnessNote && (
        <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
          {fairnessNote}
        </p>
      )}
    </InfoCard>
  )
}
