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

// How long the exit transition runs, in ms - keep in sync with the
// `duration-*` class on the panel below.
const CLOSE_ANIMATION_MS = 220

/**
 * Floating knowledge-base assistant. A round button pinned to the
 * bottom-right corner toggles a popup chat panel wired to the dedicated
 * RAG endpoint (POST /api/chat) - separate from the main /api/delivery
 * pipeline.
 */
export default function ChatWidget() {
  // `visible` keeps the panel mounted for the exit transition; `open`
  // drives the actual opacity/transform so both directions animate.
  const [visible, setVisible] = useState(false)
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([GREETING])
  const [isTyping, setIsTyping] = useState(false)
  const inFlight = useRef(false)
  const bottomRef = useRef(null)
  const inputWrapRef = useRef(null)
  const closeTimer = useRef(null)

  const openPanel = useCallback(() => {
    clearTimeout(closeTimer.current)
    setVisible(true)
    // Mount first, then flip to the "open" transform on the next frame so
    // the browser actually animates from the closed state.
    requestAnimationFrame(() => requestAnimationFrame(() => setOpen(true)))
  }, [])

  const closePanel = useCallback(() => {
    setOpen(false)
    closeTimer.current = setTimeout(() => setVisible(false), CLOSE_ANIMATION_MS)
  }, [])

  useEffect(() => () => clearTimeout(closeTimer.current), [])

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, isTyping, open])

  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && closePanel()
    window.addEventListener('keydown', onKey)
    inputWrapRef.current?.querySelector('input')?.focus()
    return () => window.removeEventListener('keydown', onKey)
  }, [open, closePanel])

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
      {/* Panel - stays mounted through the exit transition, driven by `open` */}
      {visible && (
        <div
          role="dialog"
          aria-label="SmartLogix knowledge base assistant"
          aria-hidden={!open}
          className={`fixed bottom-24 right-4 z-50 flex h-[min(32rem,calc(100vh-8rem))] w-[min(24rem,calc(100vw-2rem))]
                     origin-bottom-right flex-col overflow-hidden rounded-2xl border border-white/60
                     bg-white/85 shadow-2xl ring-1 ring-slate-900/5 backdrop-blur-xl transition-all
                     duration-200 ease-out sm:right-6
                     ${open ? 'translate-y-0 scale-100 opacity-100' : 'translate-y-3 scale-95 opacity-0'}`}
        >
          <header className="flex items-center gap-2 bg-gradient-to-r from-brand-600 to-brand-700 px-4 py-3.5 shadow-[inset_0_-1px_0_rgba(255,255,255,0.1)]">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/15 text-white ring-1 ring-white/20">
              <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="currentColor" aria-hidden="true">
                <path d="M12 3a9 9 0 0 0-9 9c0 1.6.4 3.1 1.1 4.4L3 21l4.7-1.1A9 9 0 1 0 12 3Zm-3 8a1.2 1.2 0 1 1 0 2.4A1.2 1.2 0 0 1 9 11Zm3 0a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Zm3 0a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Z" />
              </svg>
            </span>
            <div className="flex-1 leading-tight">
              <p className="text-sm font-semibold text-white">Policy assistant</p>
              <p className="text-[11px] text-brand-100">RAG knowledge base · /api/chat</p>
            </div>
            <button
              type="button"
              onClick={closePanel}
              aria-label="Close chat"
              className="rounded-md p-1 text-brand-100 transition hover:bg-white/10 hover:text-white"
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

          <div ref={inputWrapRef} className="pb-[env(safe-area-inset-bottom)]">
            <WidgetComposer onSend={ask} disabled={isTyping} />
          </div>
        </div>
      )}

      {/* Floating toggle button */}
      <button
        type="button"
        onClick={() => (open ? closePanel() : openPanel())}
        aria-label={open ? 'Close policy assistant' : 'Open policy assistant'}
        aria-expanded={open}
        className="fixed bottom-5 right-4 z-50 flex h-14 w-14 items-center justify-center rounded-full
                   bg-gradient-to-br from-brand-600 to-brand-700 text-white shadow-glow ring-4
                   ring-brand-500/15 transition duration-200 hover:scale-105
                   hover:shadow-[0_0_0_1px_rgba(79,70,229,0.15),0_16px_32px_-6px_rgba(79,70,229,0.6)]
                   focus:outline-none focus:ring-4 focus:ring-brand-300 active:scale-95 sm:right-6"
      >
        <svg
          viewBox="0 0 24 24"
          className={`h-6 w-6 transition-transform duration-200 ${open ? 'rotate-90' : 'rotate-0'}`}
          fill="currentColor"
          aria-hidden="true"
        >
          {open ? (
            <path d="m6.4 5 5.6 5.6L17.6 5 19 6.4 13.4 12 19 17.6 17.6 19 12 13.4 6.4 19 5 17.6 10.6 12 5 6.4 6.4 5Z" />
          ) : (
            <path d="M12 3a9 9 0 0 0-9 9c0 1.6.4 3.1 1.1 4.4L3 21l4.7-1.1A9 9 0 1 0 12 3Zm-3 8a1.2 1.2 0 1 1 0 2.4A1.2 1.2 0 0 1 9 11Zm3 0a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Zm3 0a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Z" />
          )}
        </svg>
      </button>
    </>
  )
}
