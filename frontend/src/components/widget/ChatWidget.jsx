import { useCallback, useEffect, useRef, useState } from 'react'
import { askPolicyQuestion } from '../../api/client'
import WidgetComposer from './WidgetComposer'
import WidgetMessage from './WidgetMessage'
import WidgetTyping from './WidgetTyping'

let counter = 0
const nextId = () => `w${++counter}`

const GREETING = {
  id: 'w-greeting',
  sender: 'bot',
  text:
    "Hi! I answer questions about SmartLogix policies, packaging rules, " +
    'warehousing, tracking and pricing straight from our knowledge base.',
}

const EXAMPLES = [
  'How are fragile items packed?',
  'Which areas do you deliver to?',
  'What happens if my delivery is delayed?',
  'How is the delivery cost calculated?',
]

/**
 * Floating knowledge-base assistant. A round button pinned to the
 * bottom-right corner toggles a popup chat panel wired to the dedicated
 * RAG endpoint (POST /api/chat) - separate from the main /api/delivery
 * pipeline.
 */
export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([GREETING])
  const [isTyping, setIsTyping] = useState(false)
  const inFlight = useRef(false)
  const bottomRef = useRef(null)
  const inputWrapRef = useRef(null)

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, isTyping, open])

  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    inputWrapRef.current?.querySelector('input')?.focus()
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const ask = useCallback(async (rawText) => {
    const text = String(rawText || '').trim()
    if (!text || inFlight.current) return
    inFlight.current = true

    setMessages((prev) => [...prev, { id: nextId(), sender: 'user', text }])
    setIsTyping(true)

    try {
      const data = await askPolicyQuestion(text)
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          sender: 'bot',
          text: data.answer || 'I could not find an answer for that.',
          sources: data.sources || [],
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: nextId(), sender: 'bot', text: err.message, error: true },
      ])
    } finally {
      setIsTyping(false)
      inFlight.current = false
    }
  }, [])

  const showExamples = messages.filter((m) => m.sender === 'user').length === 0

  return (
    <>
      {/* Panel */}
      {open && (
        <div
          role="dialog"
          aria-label="SmartLogix knowledge base assistant"
          className="fixed bottom-24 right-4 z-50 flex h-[min(32rem,calc(100vh-8rem))] w-[min(24rem,calc(100vw-2rem))]
                     flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 shadow-2xl
                     sm:right-6"
        >
          <header className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-600 text-white">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden="true">
                <path d="M12 3a9 9 0 0 0-9 9c0 1.6.4 3.1 1.1 4.4L3 21l4.7-1.1A9 9 0 1 0 12 3Zm-3 8a1.2 1.2 0 1 1 0 2.4A1.2 1.2 0 0 1 9 11Zm3 0a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Zm3 0a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Z" />
              </svg>
            </span>
            <div className="flex-1 leading-tight">
              <p className="text-sm font-semibold text-slate-900">Policy assistant</p>
              <p className="text-[11px] text-slate-500">RAG knowledge base · /api/chat</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
                <path d="m6.4 5 5.6 5.6L17.6 5 19 6.4 13.4 12 19 17.6 17.6 19 12 13.4 6.4 19 5 17.6 10.6 12 5 6.4 6.4 5Z" />
              </svg>
            </button>
          </header>

          <div className="chat-scroll flex-1 space-y-3 overflow-y-auto px-3 py-3">
            {messages.map((message) => (
              <WidgetMessage key={message.id} message={message} />
            ))}
            {isTyping && <WidgetTyping />}

            {showExamples && !isTyping && (
              <div className="flex flex-col gap-1.5 pt-1">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => ask(example)}
                    className="self-start rounded-full border border-slate-200 bg-white px-3 py-1.5
                               text-xs text-slate-600 transition hover:border-brand-300
                               hover:bg-brand-50 hover:text-brand-700"
                  >
                    {example}
                  </button>
                ))}
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div ref={inputWrapRef}>
            <WidgetComposer onSend={ask} disabled={isTyping} />
          </div>
        </div>
      )}

      {/* Floating toggle button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? 'Close policy assistant' : 'Open policy assistant'}
        aria-expanded={open}
        className="fixed bottom-5 right-4 z-50 flex h-14 w-14 items-center justify-center rounded-full
                   bg-brand-600 text-white shadow-lg transition hover:bg-brand-700
                   hover:shadow-xl focus:outline-none focus:ring-4 focus:ring-brand-300 sm:right-6"
      >
        {open ? (
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="currentColor" aria-hidden="true">
            <path d="m6.4 5 5.6 5.6L17.6 5 19 6.4 13.4 12 19 17.6 17.6 19 12 13.4 6.4 19 5 17.6 10.6 12 5 6.4 6.4 5Z" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="currentColor" aria-hidden="true">
            <path d="M12 3a9 9 0 0 0-9 9c0 1.6.4 3.1 1.1 4.4L3 21l4.7-1.1A9 9 0 1 0 12 3Zm-3 8a1.2 1.2 0 1 1 0 2.4A1.2 1.2 0 0 1 9 11Zm3 0a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Zm3 0a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Z" />
          </svg>
        )}
      </button>
    </>
  )
}
