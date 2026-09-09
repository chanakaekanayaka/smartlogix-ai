import axios from 'axios'

// Backend base URL. Override with VITE_API_BASE_URL in .env.local if needed.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // the pipeline calls an LLM, so allow up to a minute
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Run the SmartLogix agent pipeline for a plain-English delivery request.
 *
 * @param {string} query e.g. "Send a fridge from Colombo to Kandy cheaply"
 * @returns {Promise<object>} the backend's comprehensive result object
 * @throws {Error} with a human-readable `.message` on any failure
 */
export async function submitDeliveryRequest(query) {
  try {
    const { data } = await api.post('/api/delivery', { query })
    return data
  } catch (error) {
    throw new Error(toFriendlyMessage(error))
  }
}

/**
 * Ask the Retrieval Agent a company-policy / packaging / FAQ question.
 * Hits the dedicated RAG endpoint - it does NOT run the logistics pipeline.
 *
 * @param {string} message e.g. "How are fragile items packed?"
 * @returns {Promise<{answer: string, sources: object[], answer_source: string, status: string}>}
 * @throws {Error} with a human-readable `.message` on any failure
 */
export async function askPolicyQuestion(message) {
  try {
    const { data } = await api.post('/api/chat', { message })
    return data
  } catch (error) {
    throw new Error(toFriendlyMessage(error))
  }
}

/** Turn an axios error into something worth showing a user. */
function toFriendlyMessage(error) {
  if (error.response) {
    // The server answered with a 4xx / 5xx.
    const detail = error.response.data?.detail || error.response.data?.error
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
    return `Server error (${error.response.status}). Please try again.`
  }
  if (error.code === 'ECONNABORTED') {
    return 'The request timed out. The backend may still be starting up.'
  }
  if (error.request) {
    return `Could not reach the backend at ${API_BASE_URL}. Is it running (uvicorn main:app)?`
  }
  return error.message || 'Something went wrong.'
}

export default api
