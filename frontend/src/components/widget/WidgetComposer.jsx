import { useState } from 'react'

/** Input row at the bottom of the RAG widget panel. */
export default function WidgetComposer({ onSend, disabled }) {
  const [value, setValue] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 border-t border-slate-200 bg-white px-3 py-2.5"
    >
      <input
        type="text"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Ask about policies, packaging, FAQs..."
        aria-label="Policy question"
        className="min-w-0 flex-1 rounded-full border border-slate-300 px-3.5 py-2 text-sm
                   outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="Send question"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-600
                   text-white transition hover:bg-brand-700 disabled:opacity-40"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden="true">
          <path d="m3 3 18 9-18 9 3.6-9L3 3Zm4.3 9L5.6 16.2 15 12 5.6 7.8 7.3 12h6.2Z" />
        </svg>
      </button>
    </form>
  )
}
