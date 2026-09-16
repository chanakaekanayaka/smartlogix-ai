"""
backend/main.py
===============
FastAPI backend that exposes the SmartLogix multi-agent pipeline to the
React frontend.

    POST /api/delivery   { "query": "Send a fridge from Colombo to Kandy cheaply" }

runs the Coordinator (Query -> Inventory -> Warehouse -> Route -> Retrieval)
and returns one comprehensive JSON object: the parsed request, stock status,
the selected warehouse, the vehicle, the cost breakdown, the estimated time,
and a plain-English explanation.

Run it:
    cd backend
    uvicorn main:app --reload        # http://localhost:8000  (docs at /docs)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# The agent packages live at the project root; add it to sys.path so
# "uvicorn main:app" (run from the backend/ folder) can import them.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import httpx  # noqa: E402
from fastapi import Depends, FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from agents.coordinator import (  # noqa: E402
    RETRIEVAL_SERVICE_TIMEOUT,
    RETRIEVAL_SERVICE_URL,
    run_pipeline,
)
from security.auth import AuthError, User, login as auth_login  # noqa: E402
from security.config import REQUIRE_AUTH  # noqa: E402
from security.fastapi_deps import enforce_auth, get_current_user  # noqa: E402
from security.sanitization import sanitize_query  # noqa: E402

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SmartLogix API",
    description="Agentic AI logistics pipeline for the SmartLogix project (IT3041).",
    version="1.0.0",
)

# React dev servers: Create React App (3000) and Vite (5173) on either host.
ALLOWED_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Vite falls back to 5174, 5175, ... when 5173 is busy, so also allow any
# localhost / 127.0.0.1 port during development.
ALLOWED_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1):\d+"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class DeliveryRequest(BaseModel):
    """Body of POST /api/delivery - one plain-English delivery request."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The customer's delivery request in plain English.",
        examples=["Send a fridge from Colombo to Kandy at the lowest cost"],
    )


class LoginRequest(BaseModel):
    """Body of POST /api/auth/login."""

    username: str = Field(..., min_length=1, max_length=64, examples=["admin"])
    password: str = Field(..., min_length=1, max_length=256)


class ChatRequest(BaseModel):
    """Body of POST /api/chat - a policy / FAQ question for the RAG widget."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="A question about SmartLogix policies, packaging or FAQs.",
        examples=["How are fragile items packed?"],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """Tiny landing payload so hitting the base URL is not a 404."""
    return {
        "service": "SmartLogix API",
        "status": "running",
        "endpoint": "POST /api/delivery",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, object]:
    """Health check for the frontend / uptime monitoring."""
    return {"status": "ok", "auth_required": REQUIRE_AUTH}


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@app.post("/api/auth/login", tags=["auth"])
def auth_login_endpoint(request: LoginRequest) -> dict[str, Any]:
    """Exchange a username + password for a session token.

    Returns ``{ access_token, token_type, expires_in, user }``.
    Raises 401 on bad credentials.
    """
    try:
        return auth_login(request.username, request.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@app.get("/api/auth/me", tags=["auth"])
def auth_me(user: User = Depends(get_current_user)) -> dict[str, object]:
    """Return the current user - a quick way to check a token is still valid."""
    return user.public_dict()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

@app.post("/api/delivery", tags=["pipeline"])
def create_delivery_plan(
    request: DeliveryRequest,
    _user: object = Depends(enforce_auth),  # optional unless SMARTLOGIX_REQUIRE_AUTH
) -> dict[str, Any]:
    """Run the full SmartLogix agent pipeline for a delivery request.

    Returns HTTP 200 with the complete plan when the pipeline succeeds
    (including ``pipeline_status = "partial"`` when some stages degraded).
    Raises:
        * 400 - the query is empty, too short, or flagged as malicious.
        * 401 - a token is required (only when SMARTLOGIX_REQUIRE_AUTH is on).
        * 502 - an agent raised something unexpected (surfaced, not swallowed).
    """
    # Clean the free text before it reaches any agent or the LLM.
    sanitised = sanitize_query(request.query)
    if sanitised.blocked or not sanitised.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Request rejected: {'; '.join(sanitised.issues) or 'invalid input'}.",
        )
    query = sanitised.cleaned

    try:
        result = run_pipeline(query)
    except Exception as exc:  # run_pipeline shouldn't raise, but never 500 silently
        raise HTTPException(
            status_code=502,
            detail=f"SmartLogix pipeline error: {type(exc).__name__}: {exc}",
        ) from exc

    # run_pipeline reports a hard failure in the payload rather than raising.
    if result.get("pipeline_status") == "error":
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "The pipeline could not process this request."),
        )

    result["success"] = True
    if sanitised.issues:
        # Let the frontend show "we tidied your input" if it wants to.
        result["input_sanitized"] = sanitised.issues
    return result


# ---------------------------------------------------------------------------
# RAG knowledge-base chat (the floating widget)
# ---------------------------------------------------------------------------

@app.post("/api/chat", tags=["rag"])
def policy_chat(
    request: ChatRequest,
    _user: object = Depends(enforce_auth),
) -> dict[str, Any]:
    """Answer a company-policy / packaging / FAQ question from the knowledge base.

    This is the Retrieval Agent only - it does **not** run the logistics
    pipeline. Calls the standalone Retrieval Agent service
    (``agents/retrieval_service.py``) over HTTP - see ``agents/coordinator.py``
    for why that agent runs separately. Returns
    ``{ answer, sources, answer_source, status }``.
    Raises:
        * 400 - the message is empty, too short, or flagged as malicious.
        * 502 - the Retrieval Agent service is unreachable or errored.
    """
    sanitised = sanitize_query(request.message)
    if sanitised.blocked or not sanitised.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Message rejected: {'; '.join(sanitised.issues) or 'invalid input'}.",
        )

    try:
        response = httpx.post(
            f"{RETRIEVAL_SERVICE_URL}/answer",
            json={"question": sanitised.cleaned},
            timeout=RETRIEVAL_SERVICE_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # service down, timeout, bad response, etc.
        raise HTTPException(
            status_code=502,
            detail=f"Retrieval Agent service error: {type(exc).__name__}: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Local dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    # Equivalent to:  uvicorn main:app --reload --port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
