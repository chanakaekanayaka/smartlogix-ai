"""
agents/coordinator.py
=====================
The Coordinator - runs the whole SmartLogix agent pipeline end to end.

    run_pipeline("Send a fridge from Colombo to Kandy cheaply")

executes, in order:

    Query Agent      -> origin / destination / item / need
    Inventory Agent  -> stock status, product metadata
    Warehouse Agent  -> dispatch warehouse
    Route Optimizer  -> vehicle, mode, distance, cost, time
    Retrieval Agent  -> grounded natural-language explanation

then attaches map coordinates and returns one tidy, grouped dictionary for
the API / frontend. Every stage is isolated: if one fails the pipeline keeps
going with safe defaults and reports ``pipeline_status = "partial"`` rather
than crashing.

Responsible AI enforcement
--------------------------
Every response the Coordinator returns carries:

* ``explanation`` - a clear, grounded account of **why** this warehouse,
  route and cost were chosen. The Retrieval Agent's LLM prompt asks for
  exactly that; if the LLM is unavailable or its answer is too thin, the
  Coordinator substitutes a deterministic explanation built from the same
  decision facts, so the "why" is never missing.
* ``responsible_ai.fairness_note`` - a fixed statement that uniform pricing
  and warehouse rules are applied consistently across all regions.
* ``is_approximate_estimate`` / ``estimate_warning`` - an explicit flag and
  message so users never mistake the estimated cost and time for a firm quote.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

# Allow running this file directly ("python agents/coordinator.py").
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.inventory_agent import check_inventory  # noqa: E402
from agents.query_agent import process_query        # noqa: E402
from agents.retrieval_agent import explain          # noqa: E402
from agents.route_agent import optimize_route       # noqa: E402
from agents.warehouse_agent import select_warehouse  # noqa: E402
from utils.geocode import get_coordinates            # noqa: E402

__all__ = ["run_pipeline", "FAIRNESS_NOTE", "ESTIMATE_WARNING"]

# Statuses that mean a stage did its job (anything else counts as a problem).
_HEALTHY_STATUSES: frozenset[str] = frozenset({
    "in_stock", "low_stock", "out_of_stock",   # inventory (item was found)
    "ok", "ok_no_local_stock", "fallback",     # warehouse / route
    "template_only",                            # retrieval (LLM off but fine)
})

# ---------------------------------------------------------------------------
# Responsible AI - fixed compliance statements added to every response
# ---------------------------------------------------------------------------

FAIRNESS_NOTE: str = (
    "Fairness: SmartLogix applies the same rules to every customer and every "
    "region. Pricing always uses one formula - a fixed base fee, a per-kilometre "
    "distance charge, a per-kilogram weight charge, a packaging charge set by "
    "item type, and a delivery-mode multiplier - with no regional surcharge or "
    "discount. Warehouse selection follows the same proximity and capability "
    "rules for all destinations."
)

ESTIMATE_WARNING: str = (
    "The cost and delivery time shown are automated ESTIMATES calculated from "
    "historical delivery data (about 7% average error). They are not a confirmed "
    "quote. Final charges and timing are set at booking and can change with fuel "
    "prices, road and weather conditions, demand and the exact pickup/delivery "
    "addresses."
)

# The three decision points the customer-facing explanation must cover.
EXPLANATION_COVERS: tuple[str, ...] = (
    "warehouse_selection",
    "route_and_vehicle",
    "cost_calculation",
)

# Below this length the LLM/agent explanation is treated as too thin and the
# deterministic fallback is used instead.
_MIN_EXPLANATION_CHARS: int = 60

_DATA_SOURCES: tuple[str, ...] = (
    "SmartLogix historical delivery dataset (data/smartlogix_master.csv)",
    "SmartLogix policy knowledge base (ChromaDB 'knowledge' collection)",
)


# ---------------------------------------------------------------------------
# Pipeline plumbing
# ---------------------------------------------------------------------------

def _run_stage(
    name: str,
    func: Callable[[Any], dict[str, Any]],
    payload: Any,
    stage_status: dict[str, str],
) -> dict[str, Any]:
    """Call one agent, capture its status, and never let it raise."""
    try:
        result = func(payload)
        if not isinstance(result, dict):
            stage_status[name] = "error"
            return payload if isinstance(payload, dict) else {}
        # Each agent writes its own "<name>_status" key; fall back to "ok".
        status = str(
            result.get(f"{name}_status")
            or result.get("inventory_status")
            or "ok"
        )
        stage_status[name] = status
        return result
    except Exception as exc:  # noqa: BLE001 - isolate stage failures
        stage_status[name] = f"error: {type(exc).__name__}"
        return payload if isinstance(payload, dict) else {}


def _coordinates_block(state: dict[str, Any]) -> dict[str, Any]:
    """Origin / destination / warehouse pins for the frontend map."""
    return {
        "origin": get_coordinates(state.get("origin")),
        "destination": get_coordinates(state.get("destination")),
        "warehouse": get_coordinates(
            state.get("warehouse_city")
            or str(state.get("warehouse_location", "")).split(",")[0]
        ),
    }


# ---------------------------------------------------------------------------
# Responsible AI helpers
# ---------------------------------------------------------------------------

def _deterministic_explanation(state: dict[str, Any]) -> str:
    """Explanation built purely from decision facts - the guaranteed fallback.

    Explicitly answers "why this warehouse", "why this route/vehicle" and
    "how the cost was calculated" so the explainability requirement holds even
    when the LLM is unavailable.
    """
    item = (state.get("matched_item") or state.get("item") or "the item").strip()
    destination = state.get("destination") or "the destination"
    mode = state.get("delivery_mode") or "standard"
    days = state.get("estimated_days") or "a few"
    cost = state.get("estimated_cost_lkr")
    cost_text = f"LKR {cost:,}" if isinstance(cost, (int, float)) else str(cost)
    breakdown = state.get("cost_breakdown") or {}

    warehouse_reason = state.get("warehouse_message") or (
        f"{state.get('selected_warehouse', 'The assigned warehouse')} was picked "
        f"as the nearest warehouse able to handle {item} for {destination}."
    )
    route_reason = state.get("route_message") or (
        f"The shipment goes to {destination} by "
        f"{state.get('vehicle', 'a suitable vehicle')} on a {mode} service, "
        f"about {days} day(s)."
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
        cost_bits.append(f"a {mode} delivery multiplier of x{breakdown['mode_multiplier']}")
    cost_detail = (
        "; ".join(cost_bits)
        if cost_bits
        else "a base fee plus distance, weight, packaging and delivery-mode charges"
    )

    return (
        f"Warehouse: {warehouse_reason} "
        f"Route and vehicle: {route_reason} "
        f"Cost: the {cost_text} estimate is made up of {cost_detail}. "
        f"These figures are estimates, not a firm quote, and the same pricing "
        f"rules are applied to every region."
    )


def _resolve_explanation(state: dict[str, Any]) -> tuple[str, str]:
    """Return (explanation, source), guaranteeing a substantive explanation."""
    explanation = str(state.get("explanation") or "").strip()
    source = str(state.get("explanation_source") or "template")
    if len(explanation) < _MIN_EXPLANATION_CHARS:
        return _deterministic_explanation(state), "coordinator_fallback"
    return explanation, source


def _responsible_ai_block(
    state: dict[str, Any], explanation: str, explanation_source: str
) -> dict[str, Any]:
    """The Responsible AI section attached to every successful response."""
    snippets = state.get("knowledge_snippets") or []
    return {
        "explanation": explanation,
        "explanation_source": explanation_source,
        "explanation_covers": list(EXPLANATION_COVERS),
        "grounded_in_policy_count": len(snippets),
        "fairness_note": FAIRNESS_NOTE,
        "is_approximate_estimate": True,
        "estimate_warning": ESTIMATE_WARNING,
        "decision_factors": {
            "warehouse_selection": state.get("warehouse_message", ""),
            "route_and_vehicle": state.get("route_message", ""),
            "cost_calculation": state.get("cost_breakdown") or {},
        },
        "data_sources": list(_DATA_SOURCES),
    }


# ---------------------------------------------------------------------------
# Response assembly
# ---------------------------------------------------------------------------

def _shape_response(
    query: str, state: dict[str, Any], stage_status: dict[str, str]
) -> dict[str, Any]:
    """Assemble the grouped, frontend-friendly result object."""
    problems = [
        stage for stage, status in stage_status.items()
        if status not in _HEALTHY_STATUSES
    ]
    pipeline_status = "ok" if not problems else "partial"

    cost_breakdown = state.get("cost_breakdown") or {}
    explanation, explanation_source = _resolve_explanation(state)

    return {
        "query": query,
        "pipeline_status": pipeline_status,
        "stage_status": stage_status,
        "problem_stages": problems,

        # --- what the customer asked for ---
        "request": {
            "origin": state.get("origin", ""),
            "destination": state.get("destination", ""),
            "item": state.get("matched_item") or state.get("item", ""),
            "raw_item": state.get("item", ""),
            "need": state.get("need", "standard"),
        },

        # --- inventory ---
        "inventory": {
            "status": state.get("inventory_status", "unknown"),
            "available_quantity": state.get("available_quantity", 0),
            "message": state.get("stock_message", ""),
            "product_id": state.get("product_id", ""),
            "category": state.get("product_category", ""),
            "unit_weight_kg": state.get("unit_weight_kg", 0),
            "fragile": bool(state.get("fragile", False)),
            "requires_cold_storage": bool(state.get("requires_cold_storage", False)),
        },

        # --- warehouse ---
        "warehouse": {
            "id": state.get("selected_warehouse", ""),
            "location": state.get("warehouse_location", ""),
            "city": state.get("warehouse_city", ""),
            "region": state.get("warehouse_region", ""),
            "status": state.get("warehouse_status", "unknown"),
            "distance_from_origin_km": state.get("warehouse_distance_km"),
            "item_in_stock_here": bool(state.get("item_available_at_warehouse", False)),
            "message": state.get("warehouse_message", ""),
        },

        # --- route / vehicle / cost / time ---
        "route": {
            "vehicle": state.get("vehicle", ""),
            "delivery_mode": state.get("delivery_mode", ""),
            "start_city": state.get("route_start_city", ""),
            "distance_km": state.get("route_distance_km"),
            "estimated_cost_lkr": state.get("estimated_cost_lkr", 0),
            "estimated_days": state.get("estimated_days", 0),
            "cost_breakdown": cost_breakdown,
            "status": state.get("route_status", "unknown"),
            "message": state.get("route_message", ""),
            # Responsible AI: pricing fairness + estimate caveat next to the numbers.
            "is_approximate_estimate": True,
            "fairness_note": FAIRNESS_NOTE,
        },

        # --- explanation (Responsible AI: explainability) ---
        "explanation": explanation,
        "explanation_source": explanation_source,
        "knowledge_snippets": state.get("knowledge_snippets", []),

        # --- Responsible AI: explicit flags + notes ---
        "is_approximate_estimate": True,
        "estimate_warning": ESTIMATE_WARNING,
        "responsible_ai": _responsible_ai_block(state, explanation, explanation_source),

        # --- map ---
        "coordinates": _coordinates_block(state),
    }


def _degraded_response(
    query: str, error: str, stage_status: dict[str, str]
) -> dict[str, Any]:
    """Shaped response for an empty query or a total pipeline failure."""
    message = (
        "The request could not be processed, so no delivery plan or "
        "explanation is available."
    )
    return {
        "query": query,
        "pipeline_status": "error",
        "stage_status": stage_status,
        "problem_stages": [
            s for s, v in stage_status.items() if v not in _HEALTHY_STATUSES
        ] or ["query"],
        "error": error,
        "request": {
            "origin": "", "destination": "", "item": "", "raw_item": "",
            "need": "standard",
        },
        "inventory": {}, "warehouse": {}, "route": {},
        "explanation": message,
        "explanation_source": "system",
        "knowledge_snippets": [],
        "is_approximate_estimate": True,
        "estimate_warning": ESTIMATE_WARNING,
        "responsible_ai": {
            "explanation": message,
            "explanation_source": "system",
            "explanation_covers": [],
            "grounded_in_policy_count": 0,
            "fairness_note": FAIRNESS_NOTE,
            "is_approximate_estimate": True,
            "estimate_warning": ESTIMATE_WARNING,
            "decision_factors": {},
            "data_sources": list(_DATA_SOURCES),
        },
        "coordinates": {
            "origin": get_coordinates(""),
            "destination": get_coordinates(""),
            "warehouse": get_coordinates(""),
        },
    }


def run_pipeline(query: str) -> dict[str, Any]:
    """Run every agent for a plain-English delivery request.

    Args:
        query: the customer's request, e.g.
            ``"Send a fridge from Colombo to Kandy at the lowest cost"``.

    Returns:
        A grouped result dict (see :func:`_shape_response`) with keys
        ``request``, ``inventory``, ``warehouse``, ``route``, ``explanation``,
        ``responsible_ai``, ``coordinates``, plus ``pipeline_status`` /
        ``stage_status`` and the Responsible AI flags ``is_approximate_estimate``
        and ``estimate_warning``.

    Never raises - a total failure still returns a shaped object with
    ``pipeline_status = "error"``.
    """
    stage_status: dict[str, str] = {}
    clean_query = str(query or "").strip()

    if not clean_query:
        return _degraded_response(
            "", "Empty query. Describe the delivery in plain English.", stage_status
        )

    try:
        state: dict[str, Any] = {"query": clean_query}
        state = _run_stage("query", lambda _: process_query(clean_query), state, stage_status)
        state = _run_stage("inventory", check_inventory, state, stage_status)
        state = _run_stage("warehouse", select_warehouse, state, stage_status)
        state = _run_stage("route", optimize_route, state, stage_status)
        state = _run_stage("retrieval", explain, state, stage_status)
        return _shape_response(clean_query, state, stage_status)

    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        return _degraded_response(
            clean_query, f"Pipeline failed ({type(exc).__name__}): {exc}", stage_status
        )


# ---------------------------------------------------------------------------
# Standalone test hook
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import json

    sample_queries = [
        "Send a fridge from Colombo to Kandy at the lowest cost",
        "I urgently need to ship a glass vase set from Jaffna to Colombo",
        "deliver frozen food from Galle to Batticaloa",
    ]

    print("SmartLogix Coordinator - full pipeline test")
    print("=" * 64)
    for q in sample_queries:
        out = run_pipeline(q)
        print(f"\n>>> {q}")
        print(f"    pipeline_status : {out['pipeline_status']}  {out['stage_status']}")
        print(f"    warehouse: {out['warehouse'].get('id')} "
              f"{out['warehouse'].get('location')}")
        print(f"    route    : {out['route'].get('vehicle')} / "
              f"{out['route'].get('delivery_mode')} / "
              f"LKR {out['route'].get('estimated_cost_lkr')} / "
              f"{out['route'].get('estimated_days')} day(s)")
        print(f"    is_approximate_estimate : {out['is_approximate_estimate']}")
        print(f"    explanation ({out['explanation_source']}):")
        print(f"      {out['explanation']}")
        print(f"    fairness_note : {out['responsible_ai']['fairness_note'][:90]}...")

    print("\n\nresponsible_ai block for the first query:")
    print(json.dumps(run_pipeline(sample_queries[0])["responsible_ai"], indent=2,
                     ensure_ascii=False))
