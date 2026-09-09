"""
utils/dataset.py
================
Shared data-access helpers for the SmartLogix agents.

Every agent that needs the master dataset (``data/smartlogix_master.csv``)
loads it through :func:`load_master_dataset` so that path resolution, caching
and column validation happen the same way everywhere. The small type-coercion
helpers (:func:`to_int`, :func:`yes_no_to_bool`, ...) live here for the same
reason - one definition, reused by every agent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# This file is <project_root>/utils/dataset.py -> parents[1] is the root.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = PROJECT_ROOT / "data"
DEFAULT_DATASET_NAME: str = "smartlogix_master.csv"

# Columns that should be numeric if they are present in the CSV.
_KNOWN_NUMERIC_COLUMNS: tuple[str, ...] = (
    "Distance_km", "Expected_Delivery_Days", "Actual_Delivery_Days",
    "Warehouse_Capacity", "Weight_kg", "Stock_Quantity", "Reorder_Level",
    "Packaging_Cost_LKR", "Total_Cost_LKR", "On_Time",
)

__all__ = [
    "PROJECT_ROOT", "DATA_DIR", "DEFAULT_DATASET_NAME",
    "resolve_data_path", "load_master_dataset", "clear_dataset_cache",
    "build_distance_lookup", "city_distance",
    "to_int", "to_float", "yes_no_to_bool", "normalise_text",
]


# ---------------------------------------------------------------------------
# Type-coercion helpers (safe against NaN, None, stray strings)
# ---------------------------------------------------------------------------

def to_int(value: Any, default: int = 0) -> int:
    """Best-effort conversion to ``int``."""
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    """Best-effort conversion to ``float``."""
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def yes_no_to_bool(value: Any) -> bool:
    """Convert the dataset's ``'Yes'``/``'No'`` text columns to real booleans."""
    return str(value).strip().lower() in {"yes", "y", "true", "1"}


def normalise_text(value: Any) -> str:
    """Lowercase, strip, and collapse internal whitespace for safe matching."""
    return " ".join(str(value).strip().lower().split())


# ---------------------------------------------------------------------------
# Dataset loading (cached)
# ---------------------------------------------------------------------------

# Resolved-path -> prepared DataFrame. The CSV is read from disk only once
# per process; agents in the same pipeline share the cached frame.
_DATASET_CACHE: dict[str, pd.DataFrame] = {}


def resolve_data_path(name_or_path: str | Path | None = None) -> Path:
    """Turn an optional dataset name/path into an absolute :class:`Path`.

    * ``None``          -> ``data/smartlogix_master.csv`` (with a fallback for
      browser-renamed copies such as ``smartlogix_master (1).csv``).
    * a bare file name  -> looked up inside ``data/``.
    * a relative path   -> resolved against the project root.
    * an absolute path  -> returned unchanged.
    """
    if name_or_path is None:
        default = DATA_DIR / DEFAULT_DATASET_NAME
        if default.exists():
            return default
        stem, suffix = Path(DEFAULT_DATASET_NAME).stem, Path(DEFAULT_DATASET_NAME).suffix
        matches = sorted(DATA_DIR.glob(f"{stem}*{suffix}"))
        return matches[0] if matches else default

    path = Path(name_or_path)
    if path.is_absolute():
        return path
    if path.parent == Path("."):          # just a file name -> look in data/
        return DATA_DIR / path
    return PROJECT_ROOT / path              # relative path -> from project root


def load_master_dataset(
    csv_path: str | Path | None = None,
    *,
    required_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Load, validate, prepare and cache the master dataset.

    Args:
        csv_path: optional override (mainly for tests).
        required_columns: columns the caller cannot work without. A
            :class:`KeyError` is raised if any are missing.

    Returns:
        A prepared :class:`pandas.DataFrame`. Two helper columns are added
        when their source columns exist:

        * ``_order_date``  - ``Order_Date`` parsed to real datetimes.
        * ``_product_key`` - normalised ``Product_Name`` for safe matching.

        The frame is cached and shared - **treat it as read-only**.

    Raises:
        FileNotFoundError: the CSV is not on disk.
        KeyError: a required column is missing.
        ValueError: the file exists but cannot be parsed.
    """
    path = resolve_data_path(csv_path)
    cache_key = str(path)

    if cache_key not in _DATASET_CACHE:
        if not path.exists():
            raise FileNotFoundError(f"Master dataset not found at: {path}")

        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError as exc:
            raise ValueError(f"Master dataset '{path.name}' is empty.") from exc
        except pd.errors.ParserError as exc:
            raise ValueError(f"Master dataset '{path.name}' is not valid CSV: {exc}") from exc

        if frame.empty:
            raise ValueError(f"Master dataset '{path.name}' has no rows.")

        # Numeric columns -> real numbers (unparseable cells become NaN).
        for column in _KNOWN_NUMERIC_COLUMNS:
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")

        # Convenience helper columns.
        if "Order_Date" in frame.columns:
            frame["_order_date"] = pd.to_datetime(frame["Order_Date"], errors="coerce")
        if "Product_Name" in frame.columns:
            frame["_product_key"] = (
                frame["Product_Name"].astype(str).str.strip().str.lower()
                .str.replace(r"\s+", " ", regex=True)
            )

        _DATASET_CACHE[cache_key] = frame

    frame = _DATASET_CACHE[cache_key]

    if required_columns is not None:
        missing = sorted(set(required_columns) - set(frame.columns))
        if missing:
            raise KeyError(
                f"Dataset '{path.name}' is missing required column(s): {missing}"
            )

    return frame


def clear_dataset_cache() -> None:
    """Forget every cached DataFrame (useful in tests or after the CSV changes)."""
    _DATASET_CACHE.clear()


# ---------------------------------------------------------------------------
# Derived lookups shared by more than one agent
# ---------------------------------------------------------------------------

def build_distance_lookup(frame: pd.DataFrame) -> dict[tuple[str, str], float]:
    """Build a symmetric ``(city_a, city_b) -> km`` road-distance lookup.

    Distances come from the ``Origin_City`` / ``Destination_City`` /
    ``Distance_km`` columns of the master dataset, which are consistent per
    city pair. Both directions are stored, so ``lookup[("Colombo", "Kandy")]``
    and ``lookup[("Kandy", "Colombo")]`` return the same value.
    """
    for column in ("Origin_City", "Destination_City", "Distance_km"):
        if column not in frame.columns:
            raise KeyError(f"Cannot build distance lookup: missing '{column}'.")

    lookup: dict[tuple[str, str], float] = {}
    for origin, destination, distance in zip(
        frame["Origin_City"], frame["Destination_City"], frame["Distance_km"]
    ):
        if pd.isna(distance):
            continue
        a, b, km = str(origin).strip(), str(destination).strip(), float(distance)
        lookup.setdefault((a, b), km)
        lookup.setdefault((b, a), km)
    return lookup


def city_distance(
    lookup: dict[tuple[str, str], float], city_a: Any, city_b: Any
) -> float | None:
    """Look up the distance between two cities (order-independent).

    Returns ``0.0`` when the cities are the same, the known distance when the
    pair is in ``lookup``, or ``None`` when it is unknown.
    """
    a, b = str(city_a or "").strip(), str(city_b or "").strip()
    if not a or not b:
        return None
    if a.lower() == b.lower():
        return 0.0
    return lookup.get((a, b))
