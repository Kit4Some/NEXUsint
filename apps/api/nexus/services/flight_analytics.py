"""Flight analytics — trail accumulation, GPS jamming detection, holding patterns.

Ported from Shadowbroker ``fetchers/flights.py`` trail/detection logic.
State is stored in Redis instead of in-memory dicts.
"""

from __future__ import annotations

import math
from typing import Any

import structlog

logger = structlog.get_logger()

# ── Trail accumulation ───────────────────────────────────────────────────

_MAX_TRAIL_POINTS = 200
_MAX_TRAILS = 2000
_trail_cache: dict[str, list[list[float]]] = {}


def accumulate_trail(flight: dict[str, Any]) -> list[list[float]]:
    """Append current position to the aircraft's trail and return it.

    Maintains an in-memory LRU cache of trails (up to ``_MAX_TRAILS``).
    Each trail keeps the last ``_MAX_TRAIL_POINTS`` positions.
    """
    icao = flight.get("icao24", "")
    if not icao:
        return []

    lat = flight.get("lat")
    lng = flight.get("lng")
    alt = flight.get("alt", 0)
    if lat is None or lng is None:
        return _trail_cache.get(icao, [])

    import time

    point = [lat, lng, alt, time.time()]

    if icao not in _trail_cache:
        if len(_trail_cache) >= _MAX_TRAILS:
            # Evict oldest entry (FIFO)
            oldest_key = next(iter(_trail_cache))
            del _trail_cache[oldest_key]
        _trail_cache[icao] = []

    trail = _trail_cache[icao]
    trail.append(point)

    # Trim to max points
    if len(trail) > _MAX_TRAIL_POINTS:
        _trail_cache[icao] = trail[-_MAX_TRAIL_POINTS:]

    return _trail_cache[icao]


def get_trail(icao: str) -> list[list[float]]:
    """Return the current trail for an aircraft."""
    return _trail_cache.get(icao, [])


# ── GPS jamming detection ────────────────────────────────────────────────


def detect_gps_jamming(flights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect GPS jamming zones by analyzing NACp values across a grid.

    Groups aircraft by 1-degree lat/lng grid cells and flags zones where
    >25% of aircraft show degraded position accuracy (NACp < 8).

    Returns a list of jamming zone dicts with lat, lng, severity, ratio.
    """
    grid: dict[tuple[int, int], dict] = {}

    for f in flights:
        nac_p = f.get("nac_p", -1)
        lat = f.get("lat")
        lng = f.get("lng")
        if nac_p < 0 or lat is None or lng is None:
            continue

        cell = (int(lat), int(lng))
        if cell not in grid:
            grid[cell] = {"total": 0, "degraded": 0}

        grid[cell]["total"] += 1
        if nac_p < 8:
            grid[cell]["degraded"] += 1

    jamming_zones: list[dict[str, Any]] = []
    for (clat, clng), counts in grid.items():
        total = counts["total"]
        degraded = counts["degraded"]
        if total < 4:
            continue
        ratio = degraded / total
        if ratio < 0.25:
            continue

        if ratio >= 0.75:
            severity = "high"
        elif ratio >= 0.50:
            severity = "medium"
        else:
            severity = "low"

        jamming_zones.append({
            "lat": clat + 0.5,
            "lng": clng + 0.5,
            "severity": severity,
            "ratio": round(ratio, 2),
            "degraded": degraded,
            "total": total,
        })

    return jamming_zones


# ── Holding pattern detection ────────────────────────────────────────────


def _bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute initial bearing between two points in degrees."""
    rlat1 = math.radians(lat1)
    rlat2 = math.radians(lat2)
    dlng = math.radians(lng2 - lng1)
    x = math.sin(dlng) * math.cos(rlat2)
    y = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlng)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def detect_holding_pattern(flight: dict[str, Any]) -> bool:
    """Detect if an aircraft is in a holding pattern.

    Analyzes the last 8 trail points. If the cumulative bearing change
    exceeds 300 degrees, the aircraft is likely circling.
    """
    trail = flight.get("trail", [])
    if len(trail) < 8:
        return False

    recent = trail[-8:]
    total_turn = 0.0

    for i in range(1, len(recent)):
        lat1, lng1 = recent[i - 1][0], recent[i - 1][1]
        lat2, lng2 = recent[i][0], recent[i][1]

        b = _bearing(lat1, lng1, lat2, lng2)

        if i >= 2:
            prev_lat1, prev_lng1 = recent[i - 2][0], recent[i - 2][1]
            prev_b = _bearing(prev_lat1, prev_lng1, lat1, lng1)
            delta = abs(b - prev_b)
            if delta > 180:
                delta = 360 - delta
            total_turn += delta

    return total_turn > 300
