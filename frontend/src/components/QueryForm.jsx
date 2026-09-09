import { useState } from 'react'
import { EXAMPLE_QUERIES } from '../lib/format'

/**
 * The prominent delivery-request input: a text box, a submit button and a
 * few one-click example queries.
 */
export default function QueryForm({ onSubmit, loading }) {
  const [value, setValue] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    const trimmed = value.trim()
    if (trimmed && !loading) onSubmit(trimmed)
  }

  return (
    <div className="card">
      <div className="card-body">
        <label htmlFor="query" className="mb-1.5 block text-sm font-medium text-slate-700">
          Describe the delivery
        </label>

        <form onSubmit={handleSubmit} className="flex flex-col gap-2 sm:flex-row">
          <input
            id="query"
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. Send a fridge from Colombo to Kandy at the lowest cost"
            disabled={loading}
            className="flex-1 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm
                       shadow-sm outline-none transition focus:border-brand-500
                       focus:ring-2 focus:ring-brand-200 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={loading || !value.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600
                       px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition
                       hover:bg-brand-700 focus:ring-2 focus:ring-brand-300
                       disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <>
                <Spinner />
                Planning...
              </>
            ) : (
              'Plan delivery'
            )}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          <span className="text-xs text-slate-400">Try:</span>
          {EXAMPLE_QUERIES.map((example) => (
            <button
              key={example}
              type="button"
              disabled={loading}
              onClick={() => {
                setValue(example)
                onSubmit(example)
              }}
              className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1
                         text-xs text-slate-600 transition hover:border-brand-300
                         hover:bg-brand-50 hover:text-brand-700 disabled:opacity-50"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" />
    </svg>
  )
}
