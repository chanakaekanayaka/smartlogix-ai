/** "Assistant is looking that up" bubble for the RAG widget. */
export default function WidgetTyping() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-3 py-2 shadow-sm">
        {['0ms', '150ms', '300ms'].map((delay) => (
          <span
            key={delay}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
            style={{ animationDelay: delay }}
          />
        ))}
      </div>
    </div>
  )
}
