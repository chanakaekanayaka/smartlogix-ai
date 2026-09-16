"""
agents/retrieval_service.py
============================
Standalone HTTP microservice for the Retrieval Agent.

Every other agent in the SmartLogix pipeline (``agents/coordinator.py``) is
called as a plain Python function - simple, fast, in-process communication.
This one agent is deliberately run as its own FastAPI service instead, and
reached over real HTTP by:

  * ``agents/coordinator.py``  - the pipeline's retrieval stage
  * ``backend/main.py``        - the ``POST /api/chat`` policy Q&A endpoint

This is SmartLogix's defined, API-based agent-to-agent communication
protocol (IT3041 requires at least one). The underlying logic is untouched -
this file only wraps ``agents/retrieval_agent.py`` in HTTP endpoints.

Run it (from the PROJECT ROOT, not from inside agents/ - see the coordinator
for why the working directory matters):

    uvicorn agents.retrieval_service:app --reload --port 8001

Endpoints:
    GET  /health   - liveness check
    POST /explain  - wraps explain(state)
    POST /answer   - wraps answer_policy_question(question)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Allow running this file directly; also keeps it consistent with every
# other file in agents/ even though "uvicorn agents.retrieval_service:app"
# run from the project root doesn't strictly need this.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from agents.retrieval_agent import answer_policy_question, explain  # noqa: E402

# No CORS middleware here on purpose: nothing in the browser calls this
# service directly, only backend/main.py (server-to-server).
app = FastAPI(
    title="SmartLogix Retrieval Agent Service",
    description=(
        "Standalone microservice for the Retrieval Agent (RAG explanation + "
        "policy Q&A). Called over HTTP by the Coordinator and by the "
        "backend's /api/chat endpoint - SmartLogix's defined agent-to-agent "
        "communication protocol."
    ),
    version="1.0.0",
)


class AnswerRequest(BaseModel):
    """Body of POST /answer."""

    question: str = Field(..., min_length=1, max_length=500)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check for the Coordinator / backend to depend on."""
    return {"status": "ok", "service": "retrieval-agent"}


@app.post("/explain", tags=["retrieval"])
def explain_endpoint(state: dict[str, Any]) -> dict[str, Any]:
    """HTTP wrapper around agents.retrieval_agent.explain().

    ``state`` is the pipeline's accumulated decision state (item, warehouse,
    route, cost, etc.) built up by the four upstream agents. Returns that
    same dict with ``explanation`` / ``knowledge_snippets`` /
    ``explanation_source`` / ``retrieval_status`` added.
    """
    return explain(state)


@app.post("/answer", tags=["retrieval"])
def answer_endpoint(request: AnswerRequest) -> dict[str, Any]:
    """HTTP wrapper around agents.retrieval_agent.answer_policy_question()."""
    return answer_policy_question(request.question)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("agents.retrieval_service:app", host="0.0.0.0", port=8001, reload=True)
