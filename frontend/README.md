# SmartLogix Frontend

React + Vite + Tailwind **dashboard** for the SmartLogix logistics assistant,
plus a **floating RAG chat widget** for policy / FAQ questions.

- **Main dashboard** — type a plain-English request ("send a fridge from
  Colombo to Kandy cheaply"), hit *Plan delivery*, and see the full plan:
  pipeline status, headline stats, inventory, selected warehouse, an
  interactive Leaflet map of the route, the cost breakdown, and the
  Responsible AI explanation. → `POST /api/delivery`
- **Floating widget** (bottom-right button) — ask about shipping policies,
  packaging rules, warehousing and FAQs. Answers come straight from the
  ChromaDB knowledge base via the Retrieval Agent, with citations.
  → `POST /api/chat` (separate endpoint, no logistics pipeline)

## Prerequisites

- Node.js 18+ and npm
- The SmartLogix backend on `http://localhost:8000`
  (`cd backend && uvicorn main:app --reload`)

## Setup

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173 (or 5174+ if busy)
```

Backend URL defaults to `http://localhost:8000`; override with
`VITE_API_BASE_URL` in `.env.local`.

## Structure

```
src/
├── api/client.js               submitDeliveryRequest()  ->  /api/delivery
│                               askPolicyQuestion()      ->  /api/chat
├── lib/format.js               currency / status helpers, example prompts
├── components/
│   ├── Header.jsx              top bar
│   ├── QueryForm.jsx           prominent query input + submit + examples
│   ├── Dashboard.jsx           results layout
│   ├── SummaryGrid.jsx         route / item / cost / time cards
│   ├── PipelineStatus.jsx      per-agent status strip
│   ├── InventoryPanel.jsx
│   ├── WarehousePanel.jsx
│   ├── RoutePanel.jsx          vehicle + cost breakdown
│   ├── ExplanationPanel.jsx    Responsible AI explanation + sources + fairness
│   ├── RouteMap.jsx            react-leaflet map (warehouse -> destination)
│   ├── InfoCard.jsx / StatusBadge.jsx / FeedbackStates.jsx
│   └── widget/
│       ├── ChatWidget.jsx      floating button + popup panel + /api/chat state
│       ├── WidgetMessage.jsx   bubble with collapsible policy sources
│       ├── WidgetComposer.jsx  input row
│       └── WidgetTyping.jsx    typing dots
└── App.jsx                     dashboard state (query/loading/error/result) + <ChatWidget/>
```

## Tech

React 18, Vite 6, Tailwind CSS 3, axios, react-leaflet 4 + Leaflet 1.9
(OpenStreetMap tiles).
