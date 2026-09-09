"""
agents/route_agent.py
=====================
The Route Optimizer Agent - the fourth stage of the SmartLogix pipeline.

Pipeline position
-----------------
    ... -> Warehouse Agent -> **Route Optimizer** -> Coordinator / Retrieval

Given the accumulated request (origin, destination, item weight/category,
the customer's ``need`` and the selected warehouse) this agent decides:

* **vehicle**        - based on the item weight (and fragility).
* **delivery_mode**  - Economy / Standard / Express / Same-Day, from ``need``.
* **route_distance_km** - road distance the shipment actually travels
  (selected warehouse -> destination).
* **estimated_cost_lkr** - a calibrated estimate with a line-item breakdown.
* **estimated_days** - delivery time for that mode (+1 for the far North/East).

The cost formula was calibrated against ``data/smartlogix_master.csv``
(mean error ~7%). It is an *estimate* and is labelled as such.

``optimize_route`` never raises - problems surface via ``route_status``.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

# Allow running this file directly ("python agents/route_agent.py").
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from utils.dataset import (  # noqa: E402 - must follow the sys.path shim above
    build_distance_lookup,
    city_distance,
    load_master_dataset,
    normalise_text,
    to_float,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "Origin_City", "Destination_City", "Distance_km",
})

# --- Vehicle rules: (max weight kg inclusive, vehicle name) -----------------
# From the knowledge base: motorbike < 5 kg, three-wheeler <= 20 kg,
# van <= 50 kg, lorry <= 120 kg, truck above that.
_VEHICLE_BY_WEIGHT: tuple[tuple[float, str], ...] = (
    (5.0, "Motorbike"),
    (20.0, "Three Wheeler"),
    (50.0, "Van"),
    (120.0, "Lorry"),
    (math.inf, "Truck"),
)

# --- Delivery mode: customer "need" -> mode --------------------------------
_MODE_BY_NEED: dict[str, str] = {
    "cheapest": "Economy",
    "standard": "Standard",
    "fastest": "Express",   # upgraded to "Same-Day" when origin == destination
}
DEFAULT_MODE: str = "Standard"

# --- Cost model (calibrated against the dataset) --------------------------
COST_BASE_FEE_LKR: float = 200.0        # fixed booking fee
COST_PER_KM_LKR: float = 20.0           # distance charge
COST_PER_KG_LKR: float = 30.0           # weight charge
COST_MODE_MULTIPLIER: dict[str, float] = {
    "Economy": 1.0,
    "Standard": 1.15,
    "Express": 1.7,
    "Same-Day": 2.1,
}

# Packaging cost by product category (LKR), taken from the dataset.
_PACKAGING_COST_BY_CATEGORY: dict[str, int] = {
    "clothing": 120,
    "documents": 150,
    "books": 200,
    "groceries": 400,
    "auto parts": 450,
    "pharmacy": 500,
    "electronics": 600,
    "furniture": 700,
    "fragile items": 850,
    "appliances": 1200,
}
DEFAULT_PACKAGING_COST_LKR: int = 300

# --- Delivery time (days) by mode ---------------------------------------
_DAYS_BY_MODE: dict[str, int] = {
    "Economy": 4,
    "Standard": 2,
    "Express": 2,
    "Same-Day": 1,
}
# Deliveries to the far North / East take one extra day (knowledge base).
_SLOW_DESTINATIONS: frozenset[str] = frozenset({
    "jaffna", "kilinochchi", "mullaitivu", "mannar", "vavuniya",
    "batticaloa", "ampara", "trincomalee",
})

# When we have no weight, assume a small parcel.
DEFAULT_WEIGHT_KG: float = 2.0

# route_status values
STATUS_OK: str = "ok"
STATUS_NO_DISTANCE: str = "estimated_no_distance"  # distance unknown, rough estimate
STATUS_ERROR: str = "error"

_CARRIED_KEYS: tuple[str, ...] = (
    "origin", "destination", "item", "need",
    "inventory_status", "available_quantity",
    "selected_warehouse", "warehouse_location", "warehouse_status",
)

__all__ = ["optimize_route", "choose_vehicle", "estimate_cost"]


# ---------------------------------------------------------------------------
# Pure decision helpers
# ---------------------------------------------------------------------------

def choose_vehicle(weight_kg: float, *, fragile: bool = False) -> str:
    """Pick the smallest vehicle that can carry ``weight_kg``.

    Fragile parcels never go by motorbike - they are bumped up one size so
    they travel more securely (knowledge-base rule).
    """
    weight = max(0.0, to_float(weight_kg, default=DEFAULT_WEIGHT_KG))
    for max_weight, vehicle in _VEHICLE_BY_WEIGHT:
        if weight <= max_weight:
            if fragile and vehicle == "Motorbike":
                return "Three Wheeler"
            return vehicle
    return "Truck"  # unreachable (math.inf catches everything) but explicit


def choose_delivery_mode(need: Any, *, same_city: bool = False) -> str:
    """Map the customer's ``need`` to a delivery mode."""
    mode = _MODE_BY_NEED.get(normalise_text(need), DEFAULT_MODE)
    if mode == "Express" and same_city:
        return "Same-Day"
    return mode


def packaging_cost_for(category: Any) -> int:
    """Look up the packaging cost for a product category."""
    return _PACKAGING_COST_BY_CATEGORY.get(
        normalise_text(category), DEFAULT_PACKAGING_COST_LKR
    )


def estimate_cost(
    distance_km: float, weight_kg: float, mode: str, category: Any
) -> dict[str, Any]:
    """Return an itemised cost estimate.

    ``total = (base + distance charge + weight charge) * mode multiplier
    + packaging``. Every component is returned so the frontend / explanation
    can show the breakdown.
    """
    distance = max(0.0, to_float(distance_km))
    weight = max(0.0, to_float(weight_kg, default=DEFAULT_WEIGHT_KG))
    multiplier = COST_MODE_MULTIPLIER.get(mode, 1.0)
    packaging = packaging_cost_for(category)

    base = COST_BASE_FEE_LKR
    distance_charge = COST_PER_KM_LKR * distance
    weight_charge = COST_PER_KG_LKR * weight
    handling = (base + distance_charge + weight_charge) * multiplier
    total = handling + packaging

    return {
        "currency": "LKR",
        "base_fee": round(base),
        "distance_charge": round(distance_charge),
        "weight_charge": round(weight_charge),
        "mode_multiplier": multiplier,
        "packaging_cost": packaging,
        "total": round(total),
    }


def estimate_days(mode: str, destination: Any) -> int:
    """Delivery time in days for a mode, plus 1 for far North/East destinations."""
    days = _DAYS_BY_MODE.get(mode, _DAYS_BY_MODE[DEFAULT_MODE])
    if normalise_text(destination) in _SLOW_DESTINATIONS:
        days += 1
    return days


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def _carry_forward(state: Any) -> dict[str, Any]:
    base: dict[str, Any] = dict(state) if isinstance(state, dict) else {}
    for key in _CARRIED_KEYS:
        base.setdefault(key, "")
    return base


def _finalise(
    base: dict[str, Any],
    *,
    status: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base["route_status"] = status
    base["route_message"] = message
    if extra:
        base.update(extra)
    else:
        # Guarantee the contract keys exist even on the error path.
        base.setdefault("vehicle", "")
        base.setdefault("delivery_mode", "")
        base.setdefault("route_distance_km", None)
        base.setdefault("estimated_cost_lkr", 0)
        base.setdefault("estimated_days", 0)
        base.setdefault("cost_breakdown", {})
    return base


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def optimize_route(state: dict[str, Any]) -> dict[str, Any]:
    """Plan the vehicle, mode, distance, cost and time for the shipment.

    Args:
        state: the accumulated pipeline dictionary. Keys used here:
            ``destination``, ``origin``, ``warehouse_city`` /
            ``warehouse_location`` (route start), ``unit_weight_kg``,
            ``product_category``, ``fragile`` and ``need``.

    Returns:
        A new dict with all incoming keys plus ``vehicle``,
        ``delivery_mode``, ``route_distance_km``, ``estimated_cost_lkr``,
        ``cost_breakdown``, ``estimated_days``, ``route_status`` and
        ``route_message``.

    Never raises.
    """
    base = _carry_forward(state)

    try:
        if not isinstance(state, dict):
            return _finalise(
                base, status=STATUS_ERROR,
                message="Invalid input: expected the accumulated pipeline dict.",
            )

        destination = str(base.get("destination", "")).strip()
        origin = str(base.get("origin", "")).strip()

        # Route starts at the selected warehouse (fall back to the origin city).
        start_city = str(base.get("warehouse_city", "")).strip()
        if not start_city and base.get("warehouse_location"):
            start_city = str(base["warehouse_location"]).split(",")[0].strip()
        if not start_city:
            start_city = origin

        weight_kg = to_float(base.get("unit_weight_kg"), default=DEFAULT_WEIGHT_KG)
        category = base.get("product_category", "")
        fragile = bool(base.get("fragile", False))
        need = base.get("need", "")

        # --- Distance (needs the dataset) ------------------------------
        distance_km: float | None = None
        try:
            frame = load_master_dataset(required_columns=REQUIRED_COLUMNS)
            lookup = build_distance_lookup(frame)
            distance_km = city_distance(lookup, start_city, destination)
            # Last resort: origin -> destination if the warehouse leg is unknown.
            if distance_km is None:
                distance_km = city_distance(lookup, origin, destination)
        except (FileNotFoundError, KeyError, ValueError, OSError) as exc:
            # We can still produce a rough plan without a real distance.
            base["route_message_detail"] = f"distance data unavailable: {exc}"

        # --- Decisions ------------------------------------------------
        same_city = bool(
            destination and start_city
            and normalise_text(destination) == normalise_text(start_city)
        )
        vehicle = choose_vehicle(weight_kg, fragile=fragile)
        mode = choose_delivery_mode(need, same_city=same_city)

        distance_for_cost = distance_km if distance_km is not None else 0.0
        breakdown = estimate_cost(distance_for_cost, weight_kg, mode, category)
        days = estimate_days(mode, destination)

        status = STATUS_OK if distance_km is not None else STATUS_NO_DISTANCE
        if distance_km is not None:
            message = (
                f"{vehicle} on a {mode} delivery, {distance_km:.0f} km from "
                f"{start_city or 'the warehouse'} to {destination or 'the destination'}; "
                f"about {days} day(s), estimated LKR {breakdown['total']:,}."
            )
        else:
            message = (
                f"{vehicle} on a {mode} delivery; road distance to "
                f"{destination or 'the destination'} is unknown, so the cost "
                f"(LKR {breakdown['total']:,}) is a rough estimate."
            )

        return _finalise(
            base, status=status, message=message,
            extra={
                "vehicle": vehicle,
                "delivery_mode": mode,
                "route_start_city": start_city,
                "route_distance_km": (
                    round(distance_km, 1) if distance_km is not None else None
                ),
                "estimated_cost_lkr": breakdown["total"],
                "cost_breakdown": breakdown,
                "estimated_days": days,
            },
        )

    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        return _finalise(
            base, status=STATUS_ERROR,
            message=f"Unexpected route error ({type(exc).__name__}): {exc}",
        )


# ---------------------------------------------------------------------------
# Standalone test hook
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mock_states: list[dict[str, Any]] = [
        {   # light, cheap -> motorbike + economy
            "origin": "Colombo", "destination": "Kandy", "need": "cheapest",
            "warehouse_city": "Colombo", "unit_weight_kg": 2.5,
            "product_category": "Electronics", "fragile": True,
        },
        {   # heavy furniture, fast -> lorry + express
            "origin": "Galle", "destination": "Jaffna", "need": "fastest",
            "warehouse_city": "Galle", "unit_weight_kg": 80.0,
            "product_category": "Furniture", "fragile": False,
        },
        {   # same city -> same-day
            "origin": "Colombo", "destination": "Colombo", "need": "fastest",
            "warehouse_city": "Colombo", "unit_weight_kg": 0.5,
            "product_category": "Documents",
        },
        {   # missing weight / category -> safe defaults
            "origin": "Kandy", "destination": "Matara", "need": "standard",
            "warehouse_city": "Kandy",
        },
        "not a dict",  # -> error
    ]

    print("SmartLogix Route Optimizer - standalone test")
    print("=" * 64)
    for state in mock_states:
        result = optimize_route(state)
        label = state.get("destination", "-") if isinstance(state, dict) else repr(state)
        print(f"\nIN  : -> {label}")
        print(f"OUT : {result.get('vehicle') or '(none)'} / "
              f"{result.get('delivery_mode') or '-'} / "
              f"{result.get('route_distance_km')} km / "
              f"LKR {result.get('estimated_cost_lkr')} / "
              f"{result.get('estimated_days')} day(s) / status={result['route_status']}")
        print(f"      {result['route_message']}")
