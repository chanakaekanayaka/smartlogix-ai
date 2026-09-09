"""
utils/geocode.py
================
Approximate latitude/longitude for the Sri Lankan cities used in the
SmartLogix dataset. The frontend map uses these to drop pins for the
origin, the destination and the selected warehouse.

Coordinates are hand-entered town-centre points - good enough for a map
marker, not for navigation.
"""

from __future__ import annotations

from typing import Any

# Geographic centre of Sri Lanka - used when a city is unknown.
SRI_LANKA_CENTRE: dict[str, float] = {"lat": 7.8731, "lng": 80.7718}

# city (lower-case) -> (latitude, longitude)
_CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "colombo": (6.9271, 79.8612),
    "gampaha": (7.0917, 79.9997),
    "negombo": (7.2081, 79.8380),
    "kalutara": (6.5854, 79.9607),
    "kandy": (7.2906, 80.6337),
    "nuwara eliya": (6.9497, 80.7891),
    "matale": (7.4675, 80.6234),
    "dambulla": (7.8742, 80.6511),
    "galle": (6.0535, 80.2210),
    "matara": (5.9549, 80.5550),
    "hambantota": (6.1241, 81.1185),
    "jaffna": (9.6615, 80.0255),
    "kilinochchi": (9.3803, 80.3770),
    "vavuniya": (8.7514, 80.4971),
    "mannar": (8.9810, 79.9044),
    "mullaitivu": (9.2671, 80.8142),
    "anuradhapura": (8.3114, 80.4037),
    "polonnaruwa": (7.9403, 81.0188),
    "trincomalee": (8.5874, 81.2152),
    "batticaloa": (7.7170, 81.7000),
    "ampara": (7.2912, 81.6724),
    "monaragala": (6.8728, 81.3510),
    "badulla": (6.9934, 81.0550),
    "kurunegala": (7.4863, 80.3647),
    "puttalam": (8.0362, 79.8283),
    "chilaw": (7.5758, 79.7953),
    "kegalle": (7.2513, 80.3464),
    "ratnapura": (6.7056, 80.3847),
}

__all__ = ["get_coordinates", "SRI_LANKA_CENTRE"]


def get_coordinates(city: Any) -> dict[str, float | bool | str]:
    """Return ``{"lat": .., "lng": .., "city": .., "resolved": bool}`` for a city.

    Matching is case- and whitespace-insensitive. Unknown or empty cities
    fall back to the centre of Sri Lanka with ``resolved = False`` so the
    frontend can still render a pin (and optionally flag it).
    """
    name = str(city or "").strip()
    coords = _CITY_COORDINATES.get(name.lower())
    if coords is None:
        return {
            "city": name,
            "lat": SRI_LANKA_CENTRE["lat"],
            "lng": SRI_LANKA_CENTRE["lng"],
            "resolved": False,
        }
    return {"city": name, "lat": coords[0], "lng": coords[1], "resolved": True}
