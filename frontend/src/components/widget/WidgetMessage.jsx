import { useState } from 'react'

/**
 * One message in the RAG widget: a right-aligned user bubble, or a
 * left-aligned assistant bubble with an optional list of policy sources.
 */
export default function WidgetMessage({ message }) {
  const [showSources, setShowSources] = useState(false)

  if (message.sender === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-brand-600 px-3 py-2 text-sm text-white">
          {message.text}
        </div>
      </div>
    )
  }

  const sources = message.sources || []

  return (
    <div className="flex justify-start">
      <div
        className={`max-w-[90%] rounded-2xl rounded-bl-sm border px-3 py-2 text-sm ${
          message.error
            ? 'border-rose-200 bg-rose-50 text-rose-800'
            : 'border-slate-200 bg-white text-slate-700'
        }`}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{message.text}</p>

        {sources.length > 0 && (
          <div className="mt-2">
            <button
              type="button"
              onClick={() => setShowSources((v) => !v)}
              className="text-[11px] font-medium text-brand-600 hover:text-brand-700"
            >
              {showSources ? 'Hide' : 'Show'} {sources.length} source
              {sources.length === 1 ? '' : 's'}
            </button>
            {showSources && (
              <ul className="mt-1.5 space-y-1.5">
                {sources.map((source, index) => (
                  <li
                    key={index}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-[11px]"
                  >
                    {source.section && (
                      <span className="font-semibold text-slate-500">
                        {source.section}:{' '}
                      </span>
                    )}
                    <span className="text-slate-600">{source.text}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
