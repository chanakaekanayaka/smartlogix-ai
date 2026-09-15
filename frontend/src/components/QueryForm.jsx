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
      <div className="card-body sm:px-6 sm:py-5">
        <label htmlFor="query" className="mb-2 block text-sm font-semibold text-slate-700">
          Describe the delivery
        </label>

        <form onSubmit={handleSubmit} className="flex flex-col gap-2.5 sm:flex-row">
          <div className="relative flex-1">
            <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
              <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" aria-hidden="true">
                <path
                  d="M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm10 2-4.35-4.35"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </span>
            <input
              id="query"
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="e.g. Send a fridge from Colombo to Kandy at the lowest cost"
              disabled={loading}
              className="w-full rounded-full border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm
                         shadow-sm outline-none transition-all duration-200 focus:border-brand-500
                         focus:shadow-md focus:ring-4 focus:ring-brand-100 disabled:bg-slate-50"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !value.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-full bg-brand-600
                       px-6 py-3 text-sm font-semibold text-white shadow-glow transition-all duration-200
                       hover:-translate-y-0.5 hover:bg-brand-700 focus:outline-none focus:ring-4
                       focus:ring-brand-200 disabled:cursor-not-allowed disabled:opacity-50
                       disabled:shadow-none disabled:hover:-translate-y-0"
          >
            {loading ? (
              <>
                <Spinner />
                Planning...
              </>
            ) : (
              <>
                Plan delivery
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden="true">
                  <path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </>
            )}
          </button>
        </form>

        <div className="mt-3.5 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-slate-400">Try:</span>
          {EXAMPLE_QUERIES.map((example) => (
            <button
              key={example}
              type="button"
              disabled={loading}
              onClick={() => {
                setValue(example)
                onSubmit(example)
              }}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5
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
