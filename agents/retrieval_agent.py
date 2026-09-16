"""
agents/retrieval_agent.py
=========================
The Retrieval Agent - the "explain yourself" stage of the SmartLogix pipeline.

Pipeline position
-----------------
    ... -> Route Optimizer -> **Retrieval Agent** -> Coordinator -> frontend

By this point every decision has been made (item, stock, warehouse, vehicle,
mode, cost, time). This agent produces the human-readable ``explanation`` the
frontend shows the customer, grounded in the company's own policies:

1. **Retrieve** - search the ChromaDB ``knowledge`` collection (built by
   ``database/load_data.py``) for the policy paragraphs most relevant to this
   shipment.
2. **Generate** - ask Groq to turn the decision facts + those policy snippets
   into a short, plain explanation. If Groq is not configured/reachable, fall
   back to a clear template that still cites the retrieved snippets.

``explain`` never raises - retrieval / LLM problems downgrade the output but
keep the pipeline running.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

# Allow running this file directly ("python agents/retrieval_agent.py").
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from utils import llm  # noqa: E402 - must follow the sys.path shim above

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHROMA_DIR: Path = _PROJECT_ROOT / "chroma_db"
KNOWLEDGE_COLLECTION: str = "knowledge"
EMBED_MODEL_NAME: str = "all-MiniLM-L6-v2"
DEFAULT_TOP_K: int = 3

# retrieval_status values
STATUS_OK: str = "ok"                      # retrieved snippets + LLM explanation
STATUS_TEMPLATE: str = "template_only"     # snippets ok, explanation is templated
STATUS_NO_KNOWLEDGE: str = "no_knowledge"  # ChromaDB unavailable

__all__ = ["explain", "retrieve_context", "answer_policy_question"]

# Fancy Unicode punctuation an LLM may emit -> plain ASCII. Keeps the
# customer-facing string clean for React, logs and Windows consoles alike.
_PUNCTUATION_FIXES: dict[str, str] = {
    "‑": "-", "–": "-", "—": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", " ": " ",
}


def _clean_text(text: str) -> str:
    """Replace typographic Unicode with ASCII equivalents and tidy whitespace."""
    for fancy, plain in _PUNCTUATION_FIXES.items():
        text = text.replace(fancy, plain)
    return " ".join(text.split())

# Lazily-initialised ChromaDB collection handle (loading the embedding model
# takes a moment, so we only do it on first use and then reuse it).
_collection: Any | None = None
_collection_error: str | None = None
_collection_error_at: float = 0.0

# A failed attempt (e.g. a slow first-time embedding-model download that
# outran the caller's timeout) is only remembered for this long before the
# next call retries from scratch - so one transient hiccup doesn't require
# restarting the service to recover. A successful load is still cached
# forever (see below).
_RETRY_COOLDOWN_SECONDS: float = 30.0


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def _get_collection() -> Any | None:
    """Open the ChromaDB knowledge collection, or return ``None``.

    Cached forever once it succeeds. A failure is cached only for
    ``_RETRY_COOLDOWN_SECONDS`` so a transient problem retries on its own.
    """
    global _collection, _collection_error, _collection_error_at
    if _collection is not None:
        return _collection
    if _collection_error is not None:
        if time.monotonic() - _collection_error_at < _RETRY_COOLDOWN_SECONDS:
            return None
        _collection_error = None  # cooldown elapsed - retry below

    try:
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions

        if not CHROMA_DIR.exists():
            _collection_error = (
                f"'{CHROMA_DIR.name}/' not found - run: python database/load_data.py"
            )
            _collection_error_at = time.monotonic()
            return None

        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL_NAME
        )
        _collection = client.get_collection(
            name=KNOWLEDGE_COLLECTION, embedding_function=embed_fn
        )
    except Exception as exc:  # noqa: BLE001 - any failure -> no retrieval (retried later)
        _collection_error = f"{type(exc).__name__}: {exc}"
        _collection_error_at = time.monotonic()
        _collection = None
    return _collection


def retrieve_context(query_text: str, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
    """Return the ``top_k`` knowledge-base chunks most relevant to ``query_text``.

    Each item is ``{"text": str, "section": str, "score": float}`` where a
    lower ``score`` (cosine distance) means a closer match. Returns ``[]`` when
    the knowledge base is unavailable.
    """
    collection = _get_collection()
    if collection is None or not str(query_text).strip():
        return []

    try:
        result = collection.query(
            query_texts=[str(query_text)],
            n_results=max(1, top_k),
        )
    except Exception:  # noqa: BLE001 - treat a failed query as "no context"
        return []

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    snippets: list[dict[str, Any]] = []
    for index, text in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) else {}
        distance = distances[index] if index < len(distances) else None
        clean_text = str(text).strip()
        # The loader stores chunks as "[Section] body" - drop the prefix here
        # since we return the section separately.
        if clean_text.startswith("[") and "]" in clean_text:
            clean_text = clean_text.split("]", 1)[1].strip()
        snippets.append({
            "text": clean_text,
            "section": str((metadata or {}).get("section", "")).strip(),
            "score": round(float(distance), 4) if distance is not None else None,
        })
    return snippets


# ---------------------------------------------------------------------------
# Standalone RAG Q&A (used by the floating chat widget)
# ---------------------------------------------------------------------------

_QA_SYSTEM_PROMPT = (
    "You are the SmartLogix policy assistant. Answer the customer's question "
    "using ONLY the policy snippets provided. If the snippets do not contain "
    "the answer, say you do not have that information and suggest contacting "
    "support. Be concise (2-4 sentences), friendly, plain text, no bullet "
    "points. Do not invent policies, prices or figures."
)


def answer_policy_question(question: str, *, top_k: int = 4) -> dict[str, Any]:
    """Answer a company-policy / packaging / FAQ question straight from the
    ChromaDB knowledge base (retrieval-augmented, no logistics pipeline).

    Returns::

        {
          "answer": str,                # the reply to show the user
          "sources": [ {text, section, score}, ... ],
          "answer_source": "llm" | "template",
          "status": "ok" | "template_only" | "no_match" | "no_knowledge" | "empty",
        }

    Never raises.
    """
    question = str(question or "").strip()
    if not question:
        return {
            "answer": "Ask me about SmartLogix shipping policies, packaging "
                      "rules, warehousing, tracking, pricing or delivery times.",
            "sources": [],
            "answer_source": "template",
            "status": "empty",
        }

    try:
        snippets = retrieve_context(question, top_k=top_k)

        if not snippets:
            unavailable = _collection_error is not None
            return {
                "answer": (
                    "The policy knowledge base is not available right now "
                    "(run: python database/load_data.py)."
                    if unavailable else
                    "I could not find anything about that in the SmartLogix "
                    "knowledge base. Try asking about shipping, packaging, "
                    "warehousing, tracking or pricing."
                ),
                "sources": [],
                "answer_source": "template",
                "status": "no_knowledge" if unavailable else "no_match",
            }

        if llm.groq_is_configured():
            try:
                context = "\n\n".join(
                    f"[{s['section']}] {s['text']}" if s["section"] else s["text"]
                    for s in snippets
                )
                answer = _clean_text(
                    llm.chat(
                        _QA_SYSTEM_PROMPT,
                        f"QUESTION: {question}\n\nPOLICY SNIPPETS:\n{context}",
                        temperature=0.2,
                        max_tokens=800,
                    )
                )
                if answer:
                    return {
                        "answer": answer,
                        "sources": snippets,
                        "answer_source": "llm",
                        "status": "ok",
                    }
            except Exception:  # noqa: BLE001 - fall back to the top snippet
                pass

        return {
            "answer": snippets[0]["text"],
            "sources": snippets,
            "answer_source": "template",
            "status": "template_only",
        }

    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        return {
            "answer": "Something went wrong while looking that up. Please try "
                      "again.",
            "sources": [],
            "answer_source": "template",
            "status": "no_knowledge",
            "error": f"{type(exc).__name__}: {exc}",
        }


# ---------------------------------------------------------------------------
# Explanation
# ---------------------------------------------------------------------------

def _build_retrieval_query(state: dict[str, Any]) -> str:
    """Turn the decision state into a natural search query for the KB."""
    item = state.get("matched_item") or state.get("item") or "shipment"
    parts = [
        f"How is a {item} shipped from {state.get('origin', '')} to "
        f"{state.get('destination', '')}?",
        f"delivery mode {state.get('delivery_mode', '')}",
        f"vehicle {state.get('vehicle', '')}",
        "pricing and delivery time",
    ]
    if state.get("fragile"):
        parts.append("fragile item packaging and handling")
    if state.get("requires_cold_storage"):
        parts.append("cold storage and cold chain")
    if str(state.get("inventory_status")) in {"out_of_stock", "low_stock"}:
        parts.append("out of stock restock and delays")
    return " ".join(p for p in parts if p.strip())


def _facts_block(state: dict[str, Any]) -> str:
    """Ordered list of the decisions AND their reasons, for the LLM / template."""
    cost = state.get("estimated_cost_lkr")
    breakdown = state.get("cost_breakdown") or {}
    lines = [
        f"- Item: {state.get('matched_item') or state.get('item') or 'unknown'} "
        f"(category {state.get('product_category', 'n/a')}, "
        f"{state.get('unit_weight_kg', 'n/a')} kg, "
        f"fragile={bool(state.get('fragile'))}, "
        f"cold_storage={bool(state.get('requires_cold_storage'))})",
        f"- Requested route: {state.get('origin', '?')} -> {state.get('destination', '?')}",
        f"- Inventory: {state.get('inventory_status', 'unknown')} "
        f"({state.get('available_quantity', 0)} units)",
        f"- Warehouse chosen: {state.get('selected_warehouse', '?')} "
        f"({state.get('warehouse_location', '?')})",
        f"- Reason for the warehouse: {state.get('warehouse_message', 'n/a')}",
        f"- Vehicle: {state.get('vehicle', '?')}; delivery mode: "
        f"{state.get('delivery_mode', '?')}",
        f"- Reason for the vehicle/route: {state.get('route_message', 'n/a')}",
        f"- Distance shipped: {state.get('route_distance_km', 'unknown')} km",
        (f"- Estimated cost: LKR {cost:,}" if isinstance(cost, (int, float))
         else f"- Estimated cost: {cost}"),
        f"- Cost make-up (LKR): base {breakdown.get('base_fee', '?')}, "
        f"distance {breakdown.get('distance_charge', '?')}, "
        f"weight {breakdown.get('weight_charge', '?')}, "
        f"packaging {breakdown.get('packaging_cost', '?')}, "
        f"delivery-mode multiplier x{breakdown.get('mode_multiplier', '?')}",
        f"- Estimated time: {state.get('estimated_days', '?')} day(s)",
    ]
    return "\n".join(lines)


_SYSTEM_PROMPT = (
    "You are the SmartLogix delivery assistant. Using ONLY the decision facts "
    "and the company policy snippets provided, write a short, plain-language "
    "explanation (4-6 sentences, no bullet points) that clearly covers, in "
    "this order:\n"
    "1. WHY this warehouse was selected - proximity to the origin, fragile / "
    "cold-storage capability, and whether it already holds the item.\n"
    "2. WHY this vehicle and delivery mode were chosen - the item's weight and "
    "the customer's stated priority (cheapest, fastest or standard).\n"
    "3. HOW the cost was calculated - name the components (base fee, distance "
    "charge, weight charge, packaging, delivery-mode multiplier).\n"
    "Then state plainly that the cost and time are estimates, not a firm "
    "quote, and that SmartLogix applies the same pricing rules to every "
    "region. Do not invent any number or policy that is not in the facts."
)


def _template_explanation(state: dict[str, Any], snippets: list[dict[str, Any]]) -> str:
    """Deterministic explanation covering the warehouse, route and cost reasons.

    Used when the LLM is unavailable. Still explicitly answers "why this
    warehouse / route / cost" so the response stays explainable.
    """
    item = (state.get("matched_item") or state.get("item") or "your item").strip()
    destination = state.get("destination") or "the destination"
    mode = state.get("delivery_mode") or "standard"
    days = state.get("estimated_days") or "a few"
    cost = state.get("estimated_cost_lkr")
    cost_text = f"LKR {cost:,}" if isinstance(cost, (int, float)) else str(cost)
    breakdown = state.get("cost_breakdown") or {}

    warehouse_reason = state.get("warehouse_message") or (
        f"{state.get('selected_warehouse', 'The assigned warehouse')} was chosen "
        f"as the closest suitable dispatch point for {item}."
    )
    route_reason = state.get("route_message") or (
        f"The shipment travels to {destination} by {state.get('vehicle', 'a suitable vehicle')} "
        f"on a {mode} service, taking about {days} day(s)."
    )

    cost_bits = [
        f"{name} LKR {breakdown[key]:,}"
        for name, key in (
            ("a base fee of", "base_fee"),
            ("distance", "distance_charge"),
            ("weight", "weight_charge"),
            ("packaging", "packaging_cost"),
        )
        if isinstance(breakdown.get(key), (int, float))
    ]
    if breakdown.get("mode_multiplier"):
        cost_bits.append(f"a {mode} multiplier of x{breakdown['mode_multiplier']}")
    cost_detail = (
        "; ".join(cost_bits)
        if cost_bits
        else "the base fee, distance, weight, packaging and delivery-mode charges"
    )

    stock_note = ""
    if state.get("inventory_status") == "out_of_stock":
        stock_note = " Note: the item is currently out of stock, so dispatch depends on restocking."
    elif state.get("inventory_status") == "low_stock":
        stock_note = " Stock is low, so please book early."

    parts = [
        f"Warehouse: {warehouse_reason}",
        f"Route and vehicle: {route_reason}",
        f"Cost: the {cost_text} estimate is made up of {cost_detail}.{stock_note}",
        "The cost and time are estimates, not a firm quote, and the same "
        "pricing rules apply to every region.",
    ]
    if snippets:
        parts.append(f"Policy reference: {snippets[0]['text']}")
    return " ".join(parts)


def explain(state: dict[str, Any], *, top_k: int = DEFAULT_TOP_K) -> dict[str, Any]:
    """Add a grounded ``explanation`` to the pipeline state.

    Returns a new dict with all incoming keys plus:

    * ``explanation``        - the customer-facing text.
    * ``knowledge_snippets`` - the policy chunks used (list of dicts).
    * ``explanation_source`` - ``"llm"`` or ``"template"``.
    * ``retrieval_status``   - ``ok`` / ``template_only`` / ``no_knowledge``.

    Never raises.
    """
    base: dict[str, Any] = dict(state) if isinstance(state, dict) else {}

    try:
        query_text = _build_retrieval_query(base)
        snippets = retrieve_context(query_text, top_k=top_k)

        # Decide the status from what we actually got.
        if not snippets and _collection_error:
            retrieval_status = STATUS_NO_KNOWLEDGE
        else:
            retrieval_status = STATUS_OK

        explanation: str
        source: str
        if llm.groq_is_configured():
            try:
                policy_text = "\n\n".join(
                    f"[{s['section']}] {s['text']}" if s["section"] else s["text"]
                    for s in snippets
                ) or "(no specific policy snippets retrieved)"
                user_prompt = (
                    f"DECISION FACTS:\n{_facts_block(base)}\n\n"
                    f"COMPANY POLICY SNIPPETS:\n{policy_text}"
                )
                # gpt-oss style models spend some output budget on reasoning,
                # so give the answer plenty of room to finish.
                explanation = _clean_text(
                    llm.chat(
                        _SYSTEM_PROMPT, user_prompt,
                        temperature=0.2, max_tokens=1400,
                    )
                )
                source = "llm"
                if not explanation:
                    raise ValueError("empty LLM response")
            except Exception as exc:  # noqa: BLE001 - fall back to the template
                base["explanation_error"] = f"{type(exc).__name__}: {exc}"
                explanation = _template_explanation(base, snippets)
                source = "template"
                if retrieval_status == STATUS_OK:
                    retrieval_status = STATUS_TEMPLATE
        else:
            explanation = _template_explanation(base, snippets)
            source = "template"
            if retrieval_status == STATUS_OK:
                retrieval_status = STATUS_TEMPLATE

        base["explanation"] = explanation
        base["knowledge_snippets"] = snippets
        base["explanation_source"] = source
        base["retrieval_status"] = retrieval_status
        return base

    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        base["explanation"] = (
            "An explanation could not be generated, but the delivery plan above "
            "is complete."
        )
        base["knowledge_snippets"] = []
        base["explanation_source"] = "template"
        base["retrieval_status"] = STATUS_NO_KNOWLEDGE
        base["explanation_error"] = f"{type(exc).__name__}: {exc}"
        return base


# ---------------------------------------------------------------------------
# Standalone test hook
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Make sure the console can print any Unicode the LLM returns.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    mock_state = {
        "origin": "Colombo", "destination": "Jaffna",
        "item": "vase", "matched_item": "Glass Vase Set",
        "need": "fastest", "inventory_status": "in_stock",
        "available_quantity": 279, "fragile": True,
        "requires_cold_storage": False,
        "selected_warehouse": "WH006", "warehouse_location": "Kurunegala, North Western",
        "vehicle": "Three Wheeler", "delivery_mode": "Express",
        "route_distance_km": 317.0, "estimated_cost_lkr": 12450,
        "estimated_days": 3,
    }

    print("SmartLogix Retrieval Agent - standalone test")
    print("=" * 64)

    print("\n--- answer_policy_question (RAG widget) ---")
    for q in [
        "How are fragile items packed?",
        "Which areas do you deliver to?",
        "What happens if my delivery is delayed?",
    ]:
        out = answer_policy_question(q)
        print(f"\nQ: {q}")
        print(f"A ({out['answer_source']}/{out['status']}): {out['answer']}")
        print(f"   sources: {[s['section'] for s in out['sources']]}")

    print("\n--- explain (pipeline) ---")
    result = explain(mock_state)
    print(f"\nretrieval_status : {result['retrieval_status']}")
    print(f"explanation_source: {result['explanation_source']}")
    print(f"\nEXPLANATION:\n{result['explanation']}")
    print(f"\nKNOWLEDGE SNIPPETS ({len(result['knowledge_snippets'])}):")
    for snippet in result["knowledge_snippets"]:
        print(f"  - [{snippet['section']}] (score {snippet['score']}) "
              f"{snippet['text'][:100]}...")
