"""
agents/inventory_agent.py
=========================
The Inventory Agent - the second stage of the SmartLogix pipeline (IT3041).

Pipeline position
-----------------
    Query Agent  ->  **Inventory Agent**  ->  Warehouse Agent  ->  ...

The Query Agent hands us a structured request, e.g.

    {"origin": "Colombo", "destination": "Kandy",
     "item": "fridge", "need": "cheapest"}

This agent looks the item up in the master dataset
(``data/smartlogix_master.csv``), decides whether it is ``in_stock``,
``low_stock`` or ``out_of_stock``, and returns the **same dictionary with
extra keys added** so the next agent receives everything at once:

    {..., "inventory_status": "in_stock",
          "available_quantity": 353,
          "stock_message": "Refrigerator: in stock - 353 unit(s) available."}

Design notes
------------
* The CSV is order history, not a live stock table, so "current stock" is
  defined as **the most recent order record for that product** (latest
  ``Order_Date``). That row's ``Stock_Quantity`` / ``Reorder_Level`` are
  exactly what the dataset's own ``In_Stock`` / ``Low_Stock_Alert`` columns
  are derived from, so our verdict stays consistent with the data.
* Matching is case-insensitive, whitespace-trimmed, and understands a few
  everyday synonyms ("fridge" -> "Refrigerator", "tv" -> "LED Television").
* ``check_inventory`` never raises. On any problem it returns a well-formed
  dictionary with an error status so the agent pipeline keeps running.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Allow running this file directly ("python agents/inventory_agent.py"):
# put the project root on sys.path so "import utils.*" resolves.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from utils.dataset import (  # noqa: E402 - must follow the sys.path shim above
    clear_dataset_cache,
    load_master_dataset,
    normalise_text,
    to_float,
    to_int,
    yes_no_to_bool,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Columns this agent relies on. If any are missing the dataset is unusable.
REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "Order_ID", "Order_Date", "Product_Name", "Product_Category",
    "Stock_Quantity", "Reorder_Level", "Weight_kg",
    "Fragile", "Requires_Cold_Storage", "Warehouse_ID",
})

# Stock at or below this count means there is nothing to ship.
OUT_OF_STOCK_AT: int = 0
# Used only when a row's Reorder_Level is missing or unreadable.
FALLBACK_REORDER_LEVEL: int = 20

# Possible values of the "inventory_status" key in the returned dict.
STATUS_IN_STOCK: str = "in_stock"
STATUS_LOW_STOCK: str = "low_stock"
STATUS_OUT_OF_STOCK: str = "out_of_stock"
STATUS_NOT_FOUND: str = "not_found"        # item is not in the catalogue
STATUS_ERROR: str = "error"                # dataset / input problem

# Keys we expect from the Query Agent and always keep in the output.
_QUERY_KEYS: tuple[str, ...] = ("origin", "destination", "item", "need")

# Everyday words -> the exact product name used in the dataset.
ITEM_SYNONYMS: dict[str, str] = {
    "fridge": "Refrigerator",
    "refrigerator": "Refrigerator",
    "freezer": "Refrigerator",
    "tv": "LED Television",
    "television": "LED Television",
    "led tv": "LED Television",
    "smart tv": "LED Television",
    "phone": "Mobile Phone",
    "mobile": "Mobile Phone",
    "smartphone": "Mobile Phone",
    "cellphone": "Mobile Phone",
    "ac": "Air Conditioner",
    "a/c": "Air Conditioner",
    "air con": "Air Conditioner",
    "aircon": "Air Conditioner",
    "washer": "Washing Machine",
    "washing machine": "Washing Machine",
    "laptop": "Laptop",
    "notebook": "Laptop",
    "medicine": "Medicine Pack",
    "medicines": "Medicine Pack",
    "meds": "Medicine Pack",
    "drugs": "Medicine Pack",
    "documents": "Documents Package",
    "document": "Documents Package",
    "docs": "Documents Package",
    "papers": "Documents Package",
    "vegetables": "Fresh Vegetables Crate",
    "veggies": "Fresh Vegetables Crate",
    "vegetable": "Fresh Vegetables Crate",
    "frozen food": "Frozen Food Pack",
    "frozen": "Frozen Food Pack",
    "clothing": "Cotton Clothing Bale",
    "clothes": "Cotton Clothing Bale",
    "garments": "Cotton Clothing Bale",
    "books": "Books Bundle",
    "book": "Books Bundle",
    "chair": "Office Chair",
    "office chair": "Office Chair",
    "table": "Dining Table",
    "dining table": "Dining Table",
    "furniture": "Furniture Set",
    "sofa": "Furniture Set",
    "couch": "Furniture Set",
    "vase": "Glass Vase Set",
    "glass vase": "Glass Vase Set",
    "dinnerware": "Ceramic Dinnerware Set",
    "plates": "Ceramic Dinnerware Set",
    "dishes": "Ceramic Dinnerware Set",
    "crockery": "Ceramic Dinnerware Set",
    "spare parts": "Auto Spare Parts",
    "car parts": "Auto Spare Parts",
    "auto parts": "Auto Spare Parts",
}

__all__ = ["check_inventory", "load_dataset", "clear_dataset_cache"]


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_dataset(csv_path: str | Path | None = None) -> pd.DataFrame:
    """Return the master dataset as a prepared, cached DataFrame.

    Thin wrapper around :func:`utils.dataset.load_master_dataset` that pins the
    columns this agent needs. The returned frame is shared - treat it as
    read-only.

    Raises:
        FileNotFoundError: the CSV is not on disk.
        KeyError: a required column is missing.
        ValueError: the file exists but cannot be parsed.
    """
    return load_master_dataset(csv_path, required_columns=REQUIRED_COLUMNS)


# ``clear_dataset_cache`` is re-exported from utils.dataset (see imports) so
# callers of this module keep working unchanged.


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------

# Shared conversions live in utils.dataset; give them the short local names
# this module already uses so the logic below stays readable.
_normalise = normalise_text
_yes_no_to_bool = yes_no_to_bool
_safe_int = to_int
_safe_float = to_float


def _derive_product_id(product_name: str) -> str:
    """Build a deterministic product ID from the name.

    The dataset only has per-order IDs, so we synthesise a stable product key,
    e.g. ``"LED Television" -> "PRD-LED-TELEVISION"``.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(product_name).strip()).strip("-").upper()
    return f"PRD-{slug}" if slug else "PRD-UNKNOWN"


def _loose_match(query_key: str, product_key: str) -> bool:
    """True when a normalised query and product name plausibly refer to one item."""
    query_words = set(query_key.split())
    product_words = set(product_key.split())
    if not query_words or not product_words:
        return False
    # "chair" matches "office chair"; "office chair set" matches "office chair".
    if query_words <= product_words or product_words <= query_words:
        return True
    # direct substring either way ("led tv screen" vs "led tv")
    return query_key in product_key or product_key in query_key


def _classify_stock(quantity: int, reorder_level: int) -> str:
    """Apply the threshold rules to a single stock snapshot."""
    if quantity <= OUT_OF_STOCK_AT:
        return STATUS_OUT_OF_STOCK
    if quantity <= reorder_level:
        return STATUS_LOW_STOCK
    return STATUS_IN_STOCK


# ---------------------------------------------------------------------------
# Result builders (guarantee a consistent output shape)
# ---------------------------------------------------------------------------

def _carry_forward(query_result: Any) -> dict[str, Any]:
    """Start the output as a copy of the incoming request.

    Never mutates the caller's dictionary. Guarantees the four Query-Agent
    keys exist so downstream agents can rely on them.
    """
    base: dict[str, Any] = dict(query_result) if isinstance(query_result, dict) else {}
    for key in _QUERY_KEYS:
        base.setdefault(key, "")
    return base


def _finalise(
    base: dict[str, Any],
    *,
    status: str,
    quantity: int,
    message: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach the three contract keys (plus optional metadata) to ``base``."""
    base["inventory_status"] = status
    base["available_quantity"] = quantity
    base["stock_message"] = message
    if extra:
        base.update(extra)
    return base


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def check_inventory(query_result: dict[str, Any]) -> dict[str, Any]:
    """Check stock for the item in ``query_result`` and enrich the dictionary.

    Args:
        query_result: the structured output of the Query Agent. Expected keys:
            ``origin``, ``destination``, ``item``, ``need``. Only ``item`` is
            strictly required for this agent to do useful work.

    Returns:
        A new dictionary containing **every key from the input** plus:

        * ``inventory_status``   - one of ``in_stock``, ``low_stock``,
          ``out_of_stock``, ``not_found``, ``error``.
        * ``available_quantity`` - int units available (0 when unknown).
        * ``stock_message``      - short human-readable explanation.

        On the happy path it also adds metadata for the Warehouse Agent:
        ``product_id``, ``matched_item``, ``product_category``,
        ``reorder_level``, ``unit_weight_kg``, ``fragile``,
        ``requires_cold_storage``, ``stocking_warehouses``,
        ``records_analyzed`` and ``snapshot_date``.

    This function never raises - problems are reported via ``inventory_status``.
    """
    base = _carry_forward(query_result)

    try:
        # --- 1. Validate the input ------------------------------------------
        if not isinstance(query_result, dict):
            return _finalise(
                base, status=STATUS_ERROR, quantity=0,
                message=(
                    "Invalid input: expected a dict from the Query Agent, got "
                    f"{type(query_result).__name__}."
                ),
            )

        requested_item = str(base.get("item", "")).strip()
        if not requested_item:
            return _finalise(
                base, status=STATUS_ERROR, quantity=0,
                message="No item was specified in the request.",
            )

        # --- 2. Load the dataset (with targeted error handling) ------------
        try:
            frame = load_dataset()
        except FileNotFoundError as exc:
            return _finalise(
                base, status=STATUS_ERROR, quantity=0,
                message=f"Inventory data unavailable: {exc}",
            )
        except KeyError as exc:
            return _finalise(
                base, status=STATUS_ERROR, quantity=0,
                message=f"Inventory data is malformed: {exc}",
            )
        except (ValueError, OSError) as exc:
            return _finalise(
                base, status=STATUS_ERROR, quantity=0,
                message=f"Could not read the inventory data: {exc}",
            )

        # --- 3. Find the product -----------------------------------------
        product_rows = _match_product(frame, requested_item)
        if product_rows.empty:
            return _finalise(
                base, status=STATUS_NOT_FOUND, quantity=0,
                message=(
                    f"'{requested_item}' is not a recognised SmartLogix "
                    f"product, so stock cannot be checked."
                ),
            )

        # --- 4. Read the most recent stock snapshot ----------------------
        snapshot = _most_recent_snapshot(product_rows)
        canonical_name = str(snapshot["Product_Name"]).strip()
        quantity = _safe_int(snapshot["Stock_Quantity"], default=0)
        reorder_level = _safe_int(
            snapshot["Reorder_Level"], default=FALLBACK_REORDER_LEVEL
        )

        # --- 5. Apply the threshold rules -------------------------------
        status = _classify_stock(quantity, reorder_level)
        message = _build_message(canonical_name, status, quantity, reorder_level)

        # --- 6. Collect metadata for the next agent --------------------
        warehouses = sorted(
            {str(w) for w in product_rows["Warehouse_ID"].dropna().unique()}
        )
        metadata: dict[str, Any] = {
            "product_id": _derive_product_id(canonical_name),
            "matched_item": canonical_name,
            "product_category": str(snapshot.get("Product_Category", "")).strip(),
            "reorder_level": reorder_level,
            "unit_weight_kg": _safe_float(snapshot.get("Weight_kg")),
            "fragile": _yes_no_to_bool(snapshot.get("Fragile")),
            "requires_cold_storage": _yes_no_to_bool(
                snapshot.get("Requires_Cold_Storage")
            ),
            "stocking_warehouses": warehouses,
            "records_analyzed": int(len(product_rows)),
            "snapshot_date": _snapshot_date_str(snapshot),
        }

        return _finalise(
            base, status=status, quantity=quantity, message=message,
            extra=metadata,
        )

    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        # Nothing should reach here, but the pipeline must never crash.
        return _finalise(
            base, status=STATUS_ERROR, quantity=0,
            message=f"Unexpected inventory error ({type(exc).__name__}): {exc}",
        )


# ---------------------------------------------------------------------------
# Internal steps used by check_inventory
# ---------------------------------------------------------------------------

def _match_product(frame: pd.DataFrame, requested_item: str) -> pd.DataFrame:
    """Return all rows for the requested item (empty frame if none match)."""
    key = _normalise(requested_item)
    if not key:
        return frame.iloc[0:0]

    product_keys = frame["_product_key"]

    # 1. exact, normalised match
    exact = frame[product_keys == key]
    if not exact.empty:
        return exact

    # 2. everyday synonym -> canonical product name
    canonical = ITEM_SYNONYMS.get(key)
    if canonical:
        synonym_hit = frame[product_keys == _normalise(canonical)]
        if not synonym_hit.empty:
            return synonym_hit

    # 3. loose word-overlap / substring match
    loose_mask = product_keys.apply(lambda name: _loose_match(key, name))
    return frame[loose_mask]


def _most_recent_snapshot(product_rows: pd.DataFrame) -> pd.Series:
    """Pick the latest order record for a product as its 'current' stock."""
    ordered = product_rows.sort_values(
        ["_order_date", "Order_ID"], ascending=[False, False], na_position="last"
    )
    return ordered.iloc[0]


def _snapshot_date_str(snapshot: pd.Series) -> str:
    """Format the snapshot's order date as YYYY-MM-DD (or '' if unknown)."""
    raw = snapshot.get("_order_date")
    if raw is None or pd.isna(raw):
        return str(snapshot.get("Order_Date", "")).strip()
    return pd.Timestamp(raw).strftime("%Y-%m-%d")


def _build_message(
    item_name: str, status: str, quantity: int, reorder_level: int
) -> str:
    """Human-readable one-liner describing the stock situation."""
    if status == STATUS_OUT_OF_STOCK:
        return f"{item_name}: out of stock - 0 units available."
    if status == STATUS_LOW_STOCK:
        return (
            f"{item_name}: low stock - only {quantity} unit(s) left, "
            f"at or below the reorder level of {reorder_level}."
        )
    return f"{item_name}: in stock - {quantity} unit(s) available."


# ---------------------------------------------------------------------------
# Standalone test hook
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Mock outputs from the Query Agent, covering every branch.
    mock_requests: list[dict[str, Any]] = [
        {"origin": "Colombo", "destination": "Kandy",
         "item": "Refrigerator", "need": "cheapest"},          # -> in_stock
        {"origin": "Galle", "destination": "Matara",
         "item": "  dining table  ", "need": "standard"},       # -> low_stock (trimmed)
        {"origin": "Jaffna", "destination": "Vavuniya",
         "item": "auto spare parts", "need": "fastest"},        # -> out_of_stock
        {"origin": "Negombo", "destination": "Kurunegala",
         "item": "fridge", "need": "cheapest"},                 # -> in_stock (synonym)
        {"origin": "Kandy", "destination": "Colombo",
         "item": "helicopter", "need": "standard"},             # -> not_found
        {"origin": "Colombo", "destination": "Galle",
         "item": "", "need": "standard"},                       # -> error (no item)
    ]

    print("SmartLogix Inventory Agent - standalone test")
    print("=" * 60)
    for request in mock_requests:
        result = check_inventory(request)
        print(f"\nIN  : {request}")
        print(f"OUT : status={result['inventory_status']!r}, "
              f"qty={result['available_quantity']}")
        print(f"      {result['stock_message']}")
        if result["inventory_status"] in {STATUS_IN_STOCK, STATUS_LOW_STOCK,
                                          STATUS_OUT_OF_STOCK}:
            print(f"      product_id={result['product_id']}, "
                  f"fragile={result['fragile']}, "
                  f"cold_storage={result['requires_cold_storage']}, "
                  f"warehouses={result['stocking_warehouses']}")
