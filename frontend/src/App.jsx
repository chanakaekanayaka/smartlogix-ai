import { useCallback, useState } from 'react'

import { submitDeliveryRequest } from './api/client'
import Dashboard from './components/Dashboard'
import { EmptyState, ErrorState, LoadingState } from './components/FeedbackStates'
import Header from './components/Header'
import PricingPlans from './components/PricingPlans'
import QueryForm from './components/QueryForm'
import ChatWidget from './components/widget/ChatWidget'

export default function App() {
  const [view, setView] = useState('app') // 'app' | 'pricing'
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastQuery, setLastQuery] = useState('')

  const runQuery = useCallback(async (query) => {
    setLoading(true)
    setError(null)
    setLastQuery(query)
    try {
      const data = await submitDeliveryRequest(query)
      setResult(data)
    } catch (err) {
      setError(err.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="min-h-screen">
      <Header view={view} onNavigate={setView} />

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-6 sm:space-y-5 sm:px-6 sm:py-8">
        {view === 'pricing' ? (
          <PricingPlans />
        ) : (
          <>
            <QueryForm onSubmit={runQuery} loading={loading} />

            {loading && <LoadingState />}
            {!loading && error && (
              <ErrorState message={error} onRetry={() => lastQuery && runQuery(lastQuery)} />
            )}
            {!loading && !error && result && (
              <div key={lastQuery} className="animate-slide-up">
                <Dashboard data={result} />
              </div>
            )}
            {!loading && !error && !result && <EmptyState />}
          </>
        )}
      </main>

      <footer className="mx-auto max-w-7xl px-4 py-8 text-center text-xs text-slate-400 sm:px-6">
        SmartLogix - Agentic AI logistics system - university project (IT3041)
      </footer>

      {/* Floating RAG knowledge-base assistant (separate /api/chat endpoint) */}
      <ChatWidget />
    </div>
  )
}
