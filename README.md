# SmartLogix

An **Agentic AI logistics system** built as a university project.

SmartLogix uses a team of cooperating AI agents to help with logistics
tasks such as analysing shipment data, answering questions from a
logistics knowledge base, and giving recommendations. It combines:

- **CrewAI / LangChain** – to run the AI agents
- **ChromaDB + sentence-transformers** – a searchable knowledge base
  (retrieval augmented generation)
- **Groq** – the language model that powers the agents
- **Streamlit** – a simple web interface with login
- **spaCy + bcrypt** – input checking and secure passwords

## Project structure

| Folder       | What it holds                                              |
| ------------ | --------------------------------------------------------- |
| `agents/`    | The AI agents + the Coordinator that chains them          |
| `backend/`   | FastAPI server that exposes the pipeline to the frontend  |
| `frontend/`  | React + Vite + Tailwind dashboard (cards, forms)          |
| `data/`      | The dataset and knowledge-base documents                  |
| `database/`  | Script that loads the knowledge base into ChromaDB        |
| `ui/`        | The Streamlit web interface                               |
| `security/`  | Password hashing, session tokens, input sanitisation     |
| `utils/`     | Shared helpers (dataset loader, LLM client, geocoding)    |

### The agent pipeline

```
Query Agent  ->  Inventory Agent  ->  Warehouse Agent  ->  Route Optimizer  ->  Retrieval Agent
  parse text     check stock          pick warehouse       vehicle/cost/time    explain (RAG)
   (in-process function calls)                                                 (HTTP microservice)
```

`agents/coordinator.py` runs all five and returns one combined result. The
first four agents are direct, in-process Python function calls. The
**Retrieval Agent runs as its own FastAPI microservice**
(`agents/retrieval_service.py`, port 8001) and is reached over **real
HTTP** by both the Coordinator and the `/api/chat` endpoint - this is
SmartLogix's defined, API-based agent-to-agent communication protocol. If
that service isn't running, the pipeline still returns a complete result
(`pipeline_status: "partial"`) with a guaranteed fallback explanation - it
degrades gracefully rather than breaking.

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key
copy .env.example .env       # Windows  (cp on macOS/Linux)
# then edit .env and paste your GROQ_API_KEY

# 4. Load the dataset + knowledge base into ChromaDB
python database/load_data.py

# 5. Run the Retrieval Agent microservice (http://localhost:8001, docs at /docs)
#    Run this from the PROJECT ROOT, not from inside agents/.
uvicorn agents.retrieval_service:app --reload --port 8001

# 6. In a second terminal, run the API backend (http://localhost:8000, docs at /docs)
cd backend
uvicorn main:app --reload

# 7. In a third terminal, run the React frontend (http://localhost:5173)
cd frontend
npm install
npm run dev

# (Alternative UI) run the Streamlit app instead
streamlit run ui/app.py
```

Start order doesn't matter for steps 5-7 - the backend and frontend both
tolerate the Retrieval Agent service being down (or started later), just
with a "partial" result instead of a fully-grounded one until it's up.

### API

`POST /api/delivery` with `{"query": "Send a fridge from Colombo to Kandy cheaply"}`
returns the parsed request, stock status, selected warehouse, vehicle, cost
breakdown, estimated time, and a plain-English explanation. The React
dashboard in `frontend/` renders all of this.

## Security

| Endpoint                | Purpose                                             |
| ----------------------- | -------------------------------------------------- |
| `POST /api/auth/login`  | username + password → session token (bcrypt + HMAC) |
| `GET  /api/auth/me`     | check the current token / user                      |
| `POST /api/delivery`    | input is sanitised (HTML / SQLi / prompt-injection) |

- Every delivery query is cleaned before it reaches the agents or the LLM.
- Set `SMARTLOGIX_REQUIRE_AUTH=true` in `.env` to require a token on
  `/api/delivery`. Off by default so the demo frontend works without login.
- A default admin (`admin` / `changeme123`) is seeded on first run - change it:
  `python -m security.manage passwd admin "A-Better-Password-1"`
- Set `SMARTLOGIX_SECRET_KEY` in `.env` for production (a dev key is
  auto-generated otherwise).

## Commercialization

SmartLogix's target market, pricing model and deployment/go-to-market plan
are documented separately in
[`docs/COMMERCIALIZATION.md`](docs/COMMERCIALIZATION.md).

## Notes

- `.env`, the ChromaDB folder, `security/users.json` and `security/.secret_key`
  are Git-ignored and must not be uploaded.
- This project is for educational purposes.
