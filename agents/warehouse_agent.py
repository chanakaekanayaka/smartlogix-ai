"""
agents/warehouse_agent.py
=========================
The Warehouse Agent - the third stage of the SmartLogix pipeline (IT3041).

Pipeline position
-----------------
    Query Agent -> Inventory Agent -> **Warehouse Agent** -> Route Optimizer

The Inventory Agent hands us the accumulated request, e.g.

    {"origin": "Colombo", "destination": "Kandy", "item": "fridge",
     "need": "cheapest", "inventory_status": "in_stock",
     "available_quantity": 353, "fragile": False,
     "requires_cold_storage": False, "matched_item": "Refrigerator", ...}

This agent picks the warehouse the shipment should leave from and returns the
**same dictionary with three keys added**:

    {..., "selected_warehouse": "WH001",
          "warehouse_location": "Colombo, Western",
          "warehouse_status": "ok"}

Selection logic (in order of importance)
----------------------------------------
1. **Hard requirements** - if the item is fragile the warehouse must handle
   fragile goods; if it needs cold storage the warehouse must have it.
2. **Proximity** - the warehouse closest to the request's ``origin`` wins
   (a warehouse in the origin city is distance 0).
3. **Local stock** - among equally close warehouses, prefer one that already
   holds the item, then the one holding the most, then the largest warehouse.

If no warehouse satisfies the hard requirements the agent still returns a
best-effort choice with ``warehouse_status = "fallback"`` so the pipeline
never stalls. ``select_warehouse`` never raises.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Allow running this file directly ("python agents/warehouse_agent.py"):
# put the project root on sys.path so "import utils.*" resolves.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from utils.dataset import (  # noqa: E402 - must follow the sys.path shim above
    build_distance_lookup,
    load_master_dataset,
    normalise_text,
    to_int,
    yes_no_to_bool,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Columns this agent cannot work without.
REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "Warehouse_ID", "Origin_City", "Destination_City", "Distance_km",
    "Warehouse_Region", "Warehouse_Capacity", "Warehouse_Handles_Fragile",
    "Warehouse_Cold_Storage", "Product_Name", "Stock_Quantity",
    "Fragile", "Requires_Cold_Storage", "Order_Date",
})

# Values of the "warehouse_status" key in the returned dictionary.
STATUS_OK: str = "ok"                       # meets requirements, holds the item
STATUS_OK_NO_STOCK: str = "ok_no_local_stock"  # meets requirements, needs restock
STATUS_FALLBACK: str = "fallback"           # no warehouse met the hard rules
STATUS_ERROR: str = "error"                 # data / input problem

# Keys carried in from earlier agents that we always keep.
_CARRIED_KEYS: tuple[str, ...] = (
    "origin", "destination", "item", "need",
    "inventory_status", "available_quantity", "stock_message",
)

__all__ = ["select_warehouse", "build_warehouse_directory"]


# ---------------------------------------------------------------------------
# Result helpers (guarantee a consistent output shape)
# ---------------------------------------------------------------------------

def _carry_forward(pipeline_state: Any) -> dict[str, Any]:
    """Start the output as a copy of the incoming dictionary (never mutated)."""
    base: dict[str, Any] = dict(pipeline_state) if isinstance(pipeline_state, dict) else {}
    for key in _CARRIED_KEYS:
        base.setdefault(key, "")
    return base


def _finalise(
    base: dict[str, Any],
    *,
    warehouse_id: str,
    location: str,
    status: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach the three contract keys (plus optional metadata)."""
    base["selected_warehouse"] = warehouse_id
    base["warehouse_location"] = location
    base["warehouse_status"] = status
    base["warehouse_message"] = message
    if extra:
        base.update(extra)
    return base


def _error(base: dict[str, Any], message: str) -> dict[str, Any]:
    """Safe fallback dictionary used whenever selection cannot proceed."""
    return _finalise(
        base, warehouse_id="", location="", status=STATUS_ERROR, message=message,
    )


# ---------------------------------------------------------------------------
# Dataset -> warehouse knowledge
# ---------------------------------------------------------------------------

def _most_common(series: pd.Series) -> str:
    """Return the most frequent value of a text column as a stripped string."""
    return str(series.value_counts().idxmax()).strip()


def _any_yes(series: pd.Series) -> bool:
    """True if any value in the column reads as 'Yes'."""
    return bool(series.astype(str).str.strip().str.lower().eq("yes").any())


def build_warehouse_directory(frame: pd.DataFrame) -> pd.DataFrame:
    """Collapse the order history into one row per warehouse.

    Returns a DataFrame indexed by ``Warehouse_ID`` with columns
    ``city``, ``region``, ``capacity``, ``handles_fragile`` and
    ``cold_storage``. Warehouse attributes are constant across the dataset,
    so aggregating is just a tidy way to read them once.
    """
    grouped = frame.groupby("Warehouse_ID")
    directory = pd.DataFrame({
        "city": grouped["Origin_City"].agg(_most_common),
        "region": grouped["Warehouse_Region"].agg(_most_common),
        "capacity": grouped["Warehouse_Capacity"].max().map(lambda v: to_int(v)),
        "handles_fragile": grouped["Warehouse_Handles_Fragile"].agg(_any_yes),
        "cold_storage": grouped["Warehouse_Cold_Storage"].agg(_any_yes),
    })
    return directory.sort_index()


def _canonical_product_name(frame: pd.DataFrame, item_name: str) -> str:
    """Return the dataset's exact spelling of a product (or the input unchanged)."""
    key = normalise_text(item_name)
    if not key or "_product_key" not in frame.columns:
        return item_name
    rows = frame[frame["_product_key"] == key]
    return str(rows["Product_Name"].iloc[0]).strip() if not rows.empty else item_name


def _item_stock_by_warehouse(frame: pd.DataFrame, canonical_item: str) -> dict[str, int]:
    """Latest known stock of ``canonical_item`` at each warehouse."""
    key = normalise_text(canonical_item)
    if not key or "_product_key" not in frame.columns:
        return {}

    rows = frame[frame["_product_key"] == key]
    if rows.empty:
        return {}

    # Keep the most recent record per warehouse, then read its stock level.
    latest = rows.sort_values("_order_date").groupby("Warehouse_ID").tail(1)
    return {
        str(row.Warehouse_ID): to_int(row.Stock_Quantity)
        for row in latest.itertuples(index=False)
    }


def _infer_item_requirements(
    frame: pd.DataFrame, canonical_item: str
) -> tuple[bool, bool]:
    """Look up (fragile, requires_cold_storage) for an item from the dataset.

    Only used when the Inventory Agent did not already provide these flags.
    """
    key = normalise_text(canonical_item)
    if not key or "_product_key" not in frame.columns:
        return False, False
    rows = frame[frame["_product_key"] == key]
    if rows.empty:
        return False, False
    return (
        yes_no_to_bool(rows["Fragile"].iloc[0]),
        yes_no_to_bool(rows["Requires_Cold_Storage"].iloc[0]),
    )


# ---------------------------------------------------------------------------
# Core selection
# ---------------------------------------------------------------------------

def _distance_from_origin(
    origin: str, warehouse_city: str, lookup: dict[tuple[str, str], float]
) -> float:
    """Kilometres from the request origin to a warehouse city.

    Returns ``0.0`` when the origin *is* the warehouse city and
    ``math.inf`` when the distance is unknown (those warehouses rank last).
    """
    origin = origin.strip()
    if not origin:
        return math.inf
    if origin.lower() == warehouse_city.strip().lower():
        return 0.0
    return lookup.get((origin, warehouse_city.strip()), math.inf)


def _rank_candidates(
    directory: pd.DataFrame,
    *,
    origin: str,
    need_fragile: bool,
    need_cold: bool,
    distance_lookup: dict[tuple[str, str], float],
    stock_by_warehouse: dict[str, int],
) -> tuple[pd.DataFrame, bool]:
    """Apply the hard filters and sort the surviving warehouses best-first.

    Returns ``(ranked_frame, fallback_used)``. ``fallback_used`` is ``True``
    when no warehouse met the special requirements and we relaxed them.
    """
    candidates = directory
    if need_fragile:
        candidates = candidates[candidates["handles_fragile"]]
    if need_cold:
        candidates = candidates[candidates["cold_storage"]]

    fallback_used = False
    if candidates.empty:
        fallback_used = True
        candidates = directory  # relax the hard rules rather than fail

    # Attach the ranking signals.
    candidates = candidates.assign(
        distance_km=[
            _distance_from_origin(origin, city, distance_lookup)
            for city in candidates["city"]
        ],
        item_stock=[
            stock_by_warehouse.get(warehouse_id, 0)
            for warehouse_id in candidates.index
        ],
    )
    candidates["has_item"] = candidates["item_stock"] > 0

    # Deterministic ordering: sort by Warehouse_ID first so that a *stable*
    # sort on the real criteria breaks ties by ID.
    candidates = candidates.sort_index()
    ranked = candidates.sort_values(
        by=["distance_km", "has_item", "item_stock", "capacity"],
        ascending=[True, False, False, False],
        kind="stable",
    )
    return ranked, fallback_used


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def select_warehouse(pipeline_state: dict[str, Any]) -> dict[str, Any]:
    """Choose the dispatch warehouse for the current request.

    Args:
        pipeline_state: the accumulated dictionary from the Query and
            Inventory agents. Keys used here: ``origin`` (for proximity),
            ``matched_item`` / ``item`` (for local-stock preference),
            ``fragile`` and ``requires_cold_storage`` (hard requirements -
            inferred from the dataset if absent).

    Returns:
        A new dictionary with **every incoming key preserved** plus:

        * ``selected_warehouse`` - warehouse ID, e.g. ``"WH001"`` (``""`` on error).
        * ``warehouse_location`` - ``"City, Region"`` (``""`` on error).
        * ``warehouse_status``   - ``ok`` / ``ok_no_local_stock`` /
          ``fallback`` / ``error``.

        Plus metadata for the Route Optimizer: ``warehouse_message``,
        ``warehouse_city``, ``warehouse_region``, ``warehouse_capacity``,
        ``warehouse_distance_km``, ``warehouse_handles_fragile``,
        ``warehouse_cold_storage``, ``item_available_at_warehouse``,
        ``warehouse_item_stock`` and ``warehouse_candidates``.

    Never raises - failures are reported through ``warehouse_status``.
    """
    base = _carry_forward(pipeline_state)

    try:
        # --- 1. Validate input ------------------------------------------
        if not isinstance(pipeline_state, dict):
            return _error(
                base,
                "Invalid input: expected the accumulated pipeline dict, got "
                f"{type(pipeline_state).__name__}.",
            )

        origin = str(base.get("origin", "")).strip()
        # Prefer the canonical name the Inventory Agent resolved.
        item_name = str(base.get("matched_item") or base.get("item") or "").strip()

        # --- 2. Load the dataset --------------------------------------
        try:
            frame = load_master_dataset(required_columns=REQUIRED_COLUMNS)
        except FileNotFoundError as exc:
            return _error(base, f"Warehouse data unavailable: {exc}")
        except KeyError as exc:
            return _error(base, f"Warehouse data is malformed: {exc}")
        except (ValueError, OSError) as exc:
            return _error(base, f"Could not read the warehouse data: {exc}")

        # --- 3. Build the warehouse knowledge -------------------------
        directory = build_warehouse_directory(frame)
        if directory.empty:
            return _error(base, "No warehouses are defined in the dataset.")

        distance_lookup = build_distance_lookup(frame)
        # Use the dataset's own spelling of the product in stock lookups/messages.
        item_name = _canonical_product_name(frame, item_name)
        stock_by_warehouse = _item_stock_by_warehouse(frame, item_name)

        # --- 4. Decide the hard requirements ------------------------
        # Trust the Inventory Agent's flags; fall back to the dataset.
        if "fragile" in base or "requires_cold_storage" in base:
            need_fragile = bool(base.get("fragile", False))
            need_cold = bool(base.get("requires_cold_storage", False))
        else:
            need_fragile, need_cold = _infer_item_requirements(frame, item_name)

        # --- 5. Rank and pick --------------------------------------
        ranked, fallback_used = _rank_candidates(
            directory,
            origin=origin,
            need_fragile=need_fragile,
            need_cold=need_cold,
            distance_lookup=distance_lookup,
            stock_by_warehouse=stock_by_warehouse,
        )
        if ranked.empty:
            return _error(base, "No warehouse could be selected from the dataset.")

        best_id = str(ranked.index[0])
        best = ranked.iloc[0]

        # --- 6. Describe the choice ------------------------------
        distance_km = float(best["distance_km"])
        distance_known = math.isfinite(distance_km)
        item_stock_here = to_int(best["item_stock"])
        has_item = bool(best["has_item"])

        if fallback_used:
            status = STATUS_FALLBACK
        elif has_item:
            status = STATUS_OK
        else:
            status = STATUS_OK_NO_STOCK

        location = f"{best['city']}, {best['region']}"
        message = _describe_choice(
            best_id, best, origin, item_name,
            status=status, distance_known=distance_known,
            distance_km=distance_km, item_stock_here=item_stock_here,
            need_fragile=need_fragile, need_cold=need_cold,
        )

        metadata: dict[str, Any] = {
            "warehouse_city": str(best["city"]),
            "warehouse_region": str(best["region"]),
            "warehouse_capacity": to_int(best["capacity"]),
            "warehouse_distance_km": round(distance_km, 1) if distance_known else None,
            "warehouse_handles_fragile": bool(best["handles_fragile"]),
            "warehouse_cold_storage": bool(best["cold_storage"]),
            "item_available_at_warehouse": has_item,
            "warehouse_item_stock": item_stock_here,
            "warehouse_candidates": int(len(ranked)),
        }

        return _finalise(
            base, warehouse_id=best_id, location=location,
            status=status, message=message, extra=metadata,
        )

    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        return _error(
            base, f"Unexpected warehouse error ({type(exc).__name__}): {exc}"
        )


def _describe_choice(
    warehouse_id: str,
    warehouse: pd.Series,
    origin: str,
    item_name: str,
    *,
    status: str,
    distance_known: bool,
    distance_km: float,
    item_stock_here: int,
    need_fragile: bool,
    need_cold: bool,
) -> str:
    """Build the human-readable ``warehouse_message``."""
    where = f"{warehouse['city']}, {warehouse['region']}"

    if distance_known and origin:
        proximity = (
            "in the origin city"
            if distance_km == 0
            else f"{distance_km:.0f} km from {origin}"
        )
    else:
        proximity = "closest available (origin distance unknown)"

    reqs = []
    if need_fragile:
        reqs.append("fragile handling")
    if need_cold:
        reqs.append("cold storage")
    reqs_text = f" meeting {' and '.join(reqs)}" if reqs else ""

    if status == STATUS_FALLBACK:
        return (
            f"{warehouse_id} ({where}) chosen as a fallback: no warehouse "
            f"offers {' and '.join(reqs) or 'the required handling'}. "
            f"Special handling must be arranged manually."
        )

    stock_text = (
        f"holds {item_stock_here} unit(s) of {item_name}"
        if item_stock_here > 0
        else f"has no local stock of {item_name or 'the item'} (restock/transfer needed)"
    )
    return (
        f"{warehouse_id} ({where}){reqs_text} selected - {proximity}; {stock_text}."
    )


# ---------------------------------------------------------------------------
# Standalone test hook
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Mock accumulated dicts as they would arrive from the Inventory Agent.
    mock_states: list[dict[str, Any]] = [
        {   # in-stock, non-special item, origin has its own warehouse
            "origin": "Colombo", "destination": "Kandy", "item": "fridge",
            "need": "cheapest", "inventory_status": "in_stock",
            "available_quantity": 353, "matched_item": "Refrigerator",
            "fragile": False, "requires_cold_storage": False,
        },
        {   # fragile item -> must go to a fragile-handling warehouse
            "origin": "Jaffna", "destination": "Colombo", "item": "glass vase set",
            "need": "standard", "inventory_status": "in_stock",
            "available_quantity": 279, "matched_item": "Glass Vase Set",
            "fragile": True, "requires_cold_storage": False,
        },
        {   # cold-storage item -> only Colombo / Kandy / Negombo qualify
            "origin": "Galle", "destination": "Matara", "item": "frozen food",
            "need": "fastest", "inventory_status": "out_of_stock",
            "available_quantity": 0, "matched_item": "Frozen Food Pack",
            "fragile": False, "requires_cold_storage": True,
        },
        {   # origin not in the dataset -> proximity unknown, still picks one
            "origin": "Trincomalee", "destination": "Kandy", "item": "laptop",
            "need": "standard", "matched_item": "Laptop",
            "fragile": True, "requires_cold_storage": False,
        },
        {   # requirements flags missing -> inferred from the dataset
            "origin": "Kandy", "destination": "Galle", "item": "medicine pack",
        },
        {"not": "a valid pipeline dict"},  # -> error, safe fallback
    ]

    print("SmartLogix Warehouse Agent - standalone test")
    print("=" * 64)
    for state in mock_states:
        result = select_warehouse(state)
        print(f"\nIN  : origin={state.get('origin', '-')!r}, "
              f"item={state.get('matched_item') or state.get('item', '-')!r}, "
              f"fragile={state.get('fragile', 'infer')}, "
              f"cold={state.get('requires_cold_storage', 'infer')}")
        print(f"OUT : {result['selected_warehouse'] or '(none)'} | "
              f"{result['warehouse_location'] or '-'} | "
              f"status={result['warehouse_status']}")
        print(f"      {result['warehouse_message']}")
