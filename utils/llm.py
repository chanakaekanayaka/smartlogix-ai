"""
utils/llm.py
============
One place to create the Groq LLM client the SmartLogix agents share.

Keeping this here means the API key is read once, the client is reused, and
an agent can cheaply ask "is the LLM even configured?" before trying to use
it (so it can fall back gracefully when there is no key or no network).
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()  # read .env so os.getenv() sees GROQ_API_KEY / GROQ_MODEL

# Default model. Override with a GROQ_MODEL=... line in .env.
# (Plain Llama models are not available on every Groq key - this open model is.)
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

_client: Any | None = None

__all__ = ["GROQ_MODEL", "groq_is_configured", "get_groq_client", "chat"]


def groq_is_configured() -> bool:
    """True if a GROQ_API_KEY is present (does not verify it works)."""
    return bool(os.getenv("GROQ_API_KEY"))


def get_groq_client() -> Any:
    """Return a cached Groq client.

    Raises:
        RuntimeError: no ``GROQ_API_KEY`` is set.
        ImportError: the ``groq`` package is not installed.
    """
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not found. Add it to the .env file in the project root."
            )
        from groq import Groq  # imported lazily so agents that don't need it stay light

        _client = Groq(api_key=api_key)
    return _client


def chat(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 600,
) -> str:
    """Send one system+user turn to Groq and return the reply text.

    Any failure (missing key, network error, bad model) propagates to the
    caller so it can decide whether to fall back.
    """
    client = get_groq_client()
    completion = client.chat.completions.create(
        model=model or GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (completion.choices[0].message.content or "").strip()
