"""ADS-B live flight collector — async port of Shadowbroker flights.py.

Two-phase fetching pipeline:
  Phase 1 (fast):  adsb.lol 6 regions fetched in parallel (~3-5 s)
  Phase 2 (slow):  OpenSky OAuth2 gap-fill + supplemental blind-spot sources

Returns classified data directly (no shared mutable store).
"""

from __future__ import annotations

import asyncio
import math
import re
import time
from datetime import datetime, timezone
from typing import Any

import aiohttp
import structlog
from cachetools import TTLCache

from nexus.config import settings
from nexus.services.plane_alert import enrich_with_plane_alert, enrich_with_tracked_names
from nexus.utils.http_client import fetch_json

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pre-compiled regex patterns for airline code extraction (hot loop)
# ---------------------------------------------------------------------------
_RE_AIRLINE_CODE_1 = re.compile(r"^([A-Z]{3})\d")
_RE_AIRLINE_CODE_2 = re.compile(r"^([A-Z]{3})[A-Z\d]")
_RE_COMMERCIAL_CALLSIGN = re.compile(r"^[A-Z]{3}\d{1,4}[A-Z]{0,2}$")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIVATE_JET_TYPES: set[str] = {
    "G150", "G200", "G280", "GLEX", "G500", "G550", "G600", "G650", "G700",
    "GLF2", "GLF3", "GLF4", "GLF5", "GLF6", "GL5T", "GL7T", "GV", "GIV",
    "CL30", "CL35", "CL60", "BD70", "BD10",
    "CRJ1", "CRJ2",
    "C25A", "C25B", "C25C", "C500", "C501", "C510", "C525", "C526",
    "C550", "C560", "C56X", "C680", "C68A", "C700", "C750",
    "FA10", "FA20", "FA50", "FA7X", "FA8X", "F900", "F2TH", "ASTR",
    "E35L", "E545", "E550", "E55P", "LEGA", "PH10", "PH30",
    "LJ23", "LJ24", "LJ25", "LJ28", "LJ31", "LJ35", "LJ36",
    "LJ40", "LJ45", "LJ55", "LJ60", "LJ70", "LJ75",
    "H25A", "H25B", "H25C", "HA4T", "BE40", "PRM1",
    "HDJT", "PC24", "EA50", "SF50", "GALX",
}

HELI_TYPES: set[str] = {
    "R22", "R44", "R66", "B06", "B06T", "B204", "B205", "B206", "B212", "B222", "B230",
    "B407", "B412", "B427", "B429", "B430", "B505", "B525",
    "AS32", "AS35", "AS50", "AS55", "AS65",
    "EC20", "EC25", "EC30", "EC35", "EC45", "EC55", "EC75",
    "H125", "H130", "H135", "H145", "H155", "H160", "H175", "H215", "H225",
    "S55", "S58", "S61", "S64", "S70", "S76", "S92",
    "A109", "A119", "A139", "A169", "A189", "AW09",
    "MD52", "MD60", "MDHI", "MD90", "NOTR",
    "B47G", "HUEY", "GAMA", "CABR", "EXE",
}

REGIONS: list[dict[str, float]] = [
    {"lat": 39.8, "lon": -98.5, "dist": 2000},
    {"lat": 50.0, "lon": 15.0, "dist": 2000},
    {"lat": 35.0, "lon": 105.0, "dist": 2000},
    {"lat": -25.0, "lon": 133.0, "dist": 2000},
    {"lat": 0.0, "lon": 20.0, "dist": 2500},
    {"lat": -15.0, "lon": -60.0, "dist": 2000},
]

BLIND_SPOT_REGIONS: list[dict[str, Any]] = [
    {"name": "Yekaterinburg",  "lat": 56.8, "lon": 60.6,  "radius_nm": 250},
    {"name": "Novosibirsk",   "lat": 55.0, "lon": 82.9,  "radius_nm": 250},
    {"name": "Krasnoyarsk",   "lat": 56.0, "lon": 92.9,  "radius_nm": 250},
    {"name": "Vladivostok",   "lat": 43.1, "lon": 131.9, "radius_nm": 250},
    {"name": "Urumqi",        "lat": 43.8, "lon": 87.6,  "radius_nm": 250},
    {"name": "Chengdu",       "lat": 30.6, "lon": 104.1, "radius_nm": 250},
    {"name": "Lagos-Accra",   "lat": 6.5,  "lon": 3.4,   "radius_nm": 250},
    {"name": "Addis Ababa",   "lat": 9.0,  "lon": 38.7,  "radius_nm": 250},
]

OPENSKY_REGIONS: list[dict[str, Any]] = [
    {"name": "Africa",        "bbox": {"lamin": -35.0, "lomin": -20.0, "lamax": 38.0, "lomax": 55.0}},
    {"name": "Asia",          "bbox": {"lamin": 0.0,   "lomin": 30.0,  "lamax": 75.0, "lomax": 150.0}},
    {"name": "South America", "bbox": {"lamin": -60.0, "lomin": -95.0, "lamax": 15.0, "lomax": -30.0}},
]

_SUPPLEMENTAL_FETCH_INTERVAL = 120  # seconds
_OPENSKY_FETCH_INTERVAL = 300       # seconds (400 req/day budget)
_MAX_TRAIL_POINTS = 200
_MAX_TRACKED_TRAILS = 2000

# ---------------------------------------------------------------------------
# Module-level caches (persist across invocations within the same process)
# ---------------------------------------------------------------------------
_routes_cache: TTLCache[str, dict] = TTLCache(maxsize=5000, ttl=7200)
_flight_trails: dict[str, dict[str, Any]] = {}

_last_opensky_fetch: float = 0.0
_cached_opensky_flights: list[dict] = []

_last_supplemental_fetch: float = 0.0
_cached_supplemental_flights: list[dict] = []


# ---------------------------------------------------------------------------
# OpenSky OAuth2 Client (async)
# ---------------------------------------------------------------------------
class OpenSkyClient:
    """Async OAuth2 client-credentials flow for OpenSky Network API."""

    TOKEN_URL = (
        "https://auth.opensky-network.org/auth/realms/"
        "opensky-network/protocol/openid-connect/token"
    )

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._expires_at: float = 0.0

    async def get_token(self) -> str | None:
        """Return a cached token or fetch a fresh one."""
        if self._token and time.time() < self._expires_at - 60:
            return self._token

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.TOKEN_URL,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        body = await resp.json()
                        self._token = body.get("access_token")
                        self._expires_at = time.time() + body.get("expires_in", 1800)
                        logger.info("opensky.token_refreshed")
                        return self._token
                    else:
                        text = await resp.text()
                        logger.error(
                            "opensky.auth_failed",
                            status=resp.status,
                            body=text[:200],
                        )
        except Exception as exc:
            logger.error("opensky.auth_exception", error=str(exc))
        return None


_opensky_client = OpenSkyClient(
    client_id=settings.opensky_client_id,
    client_secret=settings.opensky_client_secret,
)


# ---------------------------------------------------------------------------
# Phase 1: adsb.lol region fetch (parallel)
# ---------------------------------------------------------------------------

async def _fetch_adsb_region(region: dict[str, float]) -> list[dict]:
    """Fetch a single adsb.lol region. Returns raw aircraft list."""
    url = (
        f"https://api.adsb.lol/v2/lat/{region['lat']}"
        f"/lon/{region['lon']}/dist/{int(region['dist'])}"
    )
    try:
        data = await fetch_json(url, timeout=10, retries=1)
        return data.get("ac", [])
    except Exception as exc:
        logger.warning(
            "adsb_lol.region_failed",
            lat=region["lat"],
            error=str(exc),
        )
        return []


async def _fetch_adsb_lol_all_regions() -> list[dict]:
    """Fetch all adsb.lol regions in parallel."""
    tasks = [_fetch_adsb_region(r) for r in REGIONS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_flights: list[dict] = []
    for result in results:
        if isinstance(result, list):
            all_flights.extend(result)
    return all_flights


# ---------------------------------------------------------------------------
# Route enrichment via adsb.lol routeset API
# ---------------------------------------------------------------------------

async def _fetch_routes(flights: list[dict]) -> None:
    """Fetch route info for flights and populate the routes cache."""
    callsigns_to_query: list[dict] = []
    for f in flights:
        c_sign = str(f.get("flight", "")).strip()
        if c_sign and c_sign != "UNKNOWN" and c_sign not in _routes_cache:
            callsigns_to_query.append({
                "callsign": c_sign,
                "lat": f.get("lat", 0),
                "lng": f.get("lon", 0),
            })

    if not callsigns_to_query:
        return

    batch_size = 100
    for i in range(0, len(callsigns_to_query), batch_size):
        batch = callsigns_to_query[i : i + batch_size]
        try:
            route_data = await fetch_json(
                "https://api.adsb.lol/api/0/routeset",
                method="POST",
                json_data={"planes": batch},
                timeout=15,
                retries=1,
            )
            route_list: list[dict] = []
            if isinstance(route_data, dict):
                route_list = route_data.get("value", [])
            elif isinstance(route_data, list):
                route_list = route_data

            for route in route_list:
                callsign = route.get("callsign", "")
                airports = route.get("_airports", [])
                if airports and len(airports) >= 2:
                    orig_apt = airports[0]
                    dest_apt = airports[-1]
                    _routes_cache[callsign] = {
                        "orig_name": f"{orig_apt.get('iata', '')}: {orig_apt.get('name', 'Unknown')}",
                        "dest_name": f"{dest_apt.get('iata', '')}: {dest_apt.get('name', 'Unknown')}",
                        "orig_loc": [orig_apt.get("lon", 0), orig_apt.get("lat", 0)],
                        "dest_loc": [dest_apt.get("lon", 0), dest_apt.get("lat", 0)],
                    }
            await asyncio.sleep(0.25)
        except Exception as exc:
            logger.debug("routes.batch_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Supplemental blind-spot sources (airplanes.live, adsb.fi)
# ---------------------------------------------------------------------------

async def _fetch_supplemental_sources(seen_hex: set[str]) -> list[dict]:
    """Fetch from airplanes.live and adsb.fi to fill blind-spot gaps."""
    global _last_supplemental_fetch, _cached_supplemental_flights

    now = time.time()
    if now - _last_supplemental_fetch < _SUPPLEMENTAL_FETCH_INTERVAL:
        return [
            f for f in _cached_supplemental_flights
            if f.get("hex", "").lower().strip() not in seen_hex
        ]

    new_supplemental: list[dict] = []
    supplemental_hex: set[str] = set()

    # --- airplanes.live (parallel) ---
    async def _fetch_airplaneslive(region: dict) -> list[dict]:
        url = (
            f"https://api.airplanes.live/v2/point/"
            f"{region['lat']}/{region['lon']}/{region['radius_nm']}"
        )
        try:
            data = await fetch_json(url, timeout=10, retries=1)
            return data.get("ac", [])
        except Exception as exc:
            logger.debug(
                "airplaneslive.region_failed",
                region=region["name"],
                error=str(exc),
            )
            return []

    ap_tasks = [_fetch_airplaneslive(r) for r in BLIND_SPOT_REGIONS]
    ap_results = await asyncio.gather(*ap_tasks, return_exceptions=True)

    for result in ap_results:
        if isinstance(result, list):
            for f in result:
                h = f.get("hex", "").lower().strip()
                if h and h not in seen_hex and h not in supplemental_hex:
                    f["supplemental_source"] = "airplanes.live"
                    new_supplemental.append(f)
                    supplemental_hex.add(h)

    ap_count = len(new_supplemental)

    # --- adsb.fi (sequential with 1.1 s delay to respect rate limits) ---
    for region in BLIND_SPOT_REGIONS:
        url = (
            f"https://opendata.adsb.fi/api/v3/lat/"
            f"{region['lat']}/lon/{region['lon']}/dist/{region['radius_nm']}"
        )
        try:
            data = await fetch_json(url, timeout=10, retries=1)
            for f in data.get("ac", []):
                h = f.get("hex", "").lower().strip()
                if h and h not in seen_hex and h not in supplemental_hex:
                    f["supplemental_source"] = "adsb.fi"
                    new_supplemental.append(f)
                    supplemental_hex.add(h)
        except Exception as exc:
            logger.debug(
                "adsbfi.region_failed",
                region=region["name"],
                error=str(exc),
            )
        await asyncio.sleep(1.1)

    fi_count = len(new_supplemental) - ap_count

    _cached_supplemental_flights = new_supplemental
    _last_supplemental_fetch = now

    logger.info(
        "supplemental.fetched",
        total=len(new_supplemental),
        airplanes_live=ap_count,
        adsb_fi=fi_count,
    )
    return new_supplemental


# ---------------------------------------------------------------------------
# OpenSky gap-fill
# ---------------------------------------------------------------------------

async def _fetch_opensky_gap_fill(seen_hex: set[str]) -> list[dict]:
    """Fetch aircraft from OpenSky for regions with poor adsb.lol coverage."""
    global _last_opensky_fetch, _cached_opensky_flights

    now = time.time()
    if now - _last_opensky_fetch < _OPENSKY_FETCH_INTERVAL:
        return [
            f for f in _cached_opensky_flights
            if f.get("hex", "").lower().strip() not in seen_hex
        ]

    token = await _opensky_client.get_token()
    if not token:
        return [
            f for f in _cached_opensky_flights
            if f.get("hex", "").lower().strip() not in seen_hex
        ]

    new_flights: list[dict] = []
    headers = {"Authorization": f"Bearer {token}"}

    for os_reg in OPENSKY_REGIONS:
        bb = os_reg["bbox"]
        url = (
            f"https://opensky-network.org/api/states/all"
            f"?lamin={bb['lamin']}&lomin={bb['lomin']}"
            f"&lamax={bb['lamax']}&lomax={bb['lomax']}"
        )
        try:
            data = await fetch_json(url, timeout=15, retries=1, headers=headers)
            states = data.get("states") or []
            logger.info(
                "opensky.region_fetched",
                region=os_reg["name"],
                count=len(states),
            )
            for s in states:
                new_flights.append({
                    "hex": s[0],
                    "flight": s[1].strip() if s[1] else "UNKNOWN",
                    "r": s[2],
                    "lon": s[5],
                    "lat": s[6],
                    "alt_baro": (s[7] * 3.28084) if s[7] else 0,
                    "track": s[10] or 0,
                    "gs": (s[9] * 1.94384) if s[9] else 0,
                    "t": "Unknown",
                    "is_opensky": True,
                })
        except Exception as exc:
            logger.error(
                "opensky.region_failed",
                region=os_reg["name"],
                error=str(exc),
            )

    _cached_opensky_flights = new_flights
    _last_opensky_fetch = now

    return [
        f for f in new_flights
        if f.get("hex", "").lower().strip() not in seen_hex
    ]


# ---------------------------------------------------------------------------
# Normalization: raw ADS-B dict → clean flight dict
# ---------------------------------------------------------------------------

def _normalize_flight(f: dict) -> dict | None:
    """Convert a raw ADS-B aircraft dict to a normalized flight dict.

    Returns ``None`` if the record should be skipped.
    """
    lat = f.get("lat")
    lng = f.get("lon")
    if lat is None or lng is None:
        return None

    model_upper = f.get("t", "").upper()
    if model_upper == "TWR":
        return None

    flight_str = str(f.get("flight", "UNKNOWN")).strip()
    if not flight_str or flight_str == "UNKNOWN":
        flight_str = str(f.get("hex", "Unknown"))

    # Route lookup
    cached_route = _routes_cache.get(flight_str)
    origin_name = cached_route["orig_name"] if cached_route else "UNKNOWN"
    dest_name = cached_route["dest_name"] if cached_route else "UNKNOWN"
    origin_loc = cached_route["orig_loc"] if cached_route else None
    dest_loc = cached_route["dest_loc"] if cached_route else None

    # Airline code extraction
    airline_code = ""
    match = _RE_AIRLINE_CODE_1.match(flight_str)
    if not match:
        match = _RE_AIRLINE_CODE_2.match(flight_str)
    if match:
        airline_code = match.group(1)

    # Altitude (feet → metres)
    alt_raw = f.get("alt_baro")
    alt_value = 0.0
    if isinstance(alt_raw, (int, float)):
        alt_value = alt_raw * 0.3048

    # Speed
    gs_knots = f.get("gs")
    speed_knots = round(gs_knots, 1) if isinstance(gs_knots, (int, float)) else None

    heading = f.get("track") or 0
    ac_category = "heli" if model_upper in HELI_TYPES else "plane"

    return {
        "callsign": flight_str,
        "country": f.get("r", "N/A"),
        "lng": float(lng),
        "lat": float(lat),
        "alt": alt_value,
        "heading": heading,
        "type": "flight",
        "origin_loc": origin_loc,
        "dest_loc": dest_loc,
        "origin_name": origin_name,
        "dest_name": dest_name,
        "registration": f.get("r", "N/A"),
        "model": f.get("t", "Unknown"),
        "icao24": f.get("hex", ""),
        "speed_knots": speed_knots,
        "squawk": f.get("squawk", ""),
        "airline_code": airline_code,
        "aircraft_category": ac_category,
        "nac_p": f.get("nac_p"),
    }


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _classify_flights(
    flights: list[dict],
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Classify normalized flights into (commercial, private_jets, private_ga, tracked)."""
    commercial: list[dict] = []
    private_jets: list[dict] = []
    private_ga: list[dict] = []
    tracked: list[dict] = []

    for f in flights:
        enrich_with_plane_alert(f)
        enrich_with_tracked_names(f)

        callsign = f.get("callsign", "").strip().upper()
        is_commercial_format = bool(_RE_COMMERCIAL_CALLSIGN.match(callsign))

        if f.get("alert_category"):
            f["type"] = "tracked_flight"
            tracked.append(f)
        elif f.get("airline_code") or is_commercial_format:
            f["type"] = "commercial_flight"
            commercial.append(f)
        elif f.get("model", "").upper() in PRIVATE_JET_TYPES:
            f["type"] = "private_jet"
            private_jets.append(f)
        else:
            f["type"] = "private_ga"
            private_ga.append(f)

    return commercial, private_jets, private_ga, tracked


# ---------------------------------------------------------------------------
# Smart merge (protect against partial API failures)
# ---------------------------------------------------------------------------

def _smart_merge(
    new_list: list[dict],
    old_list: list[dict],
    now: float,
    max_stale_s: float = 120.0,
) -> list[dict]:
    """Merge new flights with old, keeping recently-seen entries from old data."""
    by_icao: dict[str, dict] = {}
    for f in old_list:
        icao = f.get("icao24", "")
        if icao:
            f.setdefault("_seen_at", now)
            if (now - f.get("_seen_at", now)) < max_stale_s:
                by_icao[icao] = f
    for f in new_list:
        icao = f.get("icao24", "")
        if icao:
            f["_seen_at"] = now
            by_icao[icao] = f
    return list(by_icao.values())


# ---------------------------------------------------------------------------
# Trail accumulation
# ---------------------------------------------------------------------------

def _accumulate_trails(
    flight_lists: list[list[dict]],
    now_ts: float,
    *,
    check_route: bool = True,
) -> int:
    """Update ``_flight_trails`` from all flight lists. Returns count of active trails."""
    trail_count = 0

    for flist in flight_lists:
        for f in flist:
            hex_id = f.get("icao24", "").lower()
            if not hex_id:
                continue

            if check_route and f.get("origin_name", "UNKNOWN") != "UNKNOWN":
                f["trail"] = []
                continue

            lat, lng, alt = f.get("lat"), f.get("lng"), f.get("alt", 0)
            if lat is None or lng is None:
                f["trail"] = _flight_trails.get(hex_id, {}).get("points", [])
                continue

            point = [round(lat, 5), round(lng, 5), round(alt, 1), round(now_ts)]

            if hex_id not in _flight_trails:
                _flight_trails[hex_id] = {"points": [], "last_seen": now_ts}

            trail_data = _flight_trails[hex_id]
            pts = trail_data["points"]
            if pts and pts[-1][0] == point[0] and pts[-1][1] == point[1]:
                trail_data["last_seen"] = now_ts
            else:
                pts.append(point)
                trail_data["last_seen"] = now_ts

            if len(pts) > _MAX_TRAIL_POINTS:
                trail_data["points"] = pts[-_MAX_TRAIL_POINTS:]

            f["trail"] = trail_data["points"]
            trail_count += 1

    return trail_count


def _prune_trails(now_ts: float, tracked_hexes: set[str]) -> int:
    """Remove stale trails and enforce max cache size. Returns pruned count."""
    stale_keys = [
        k
        for k, v in _flight_trails.items()
        if v["last_seen"] < (now_ts - 1800 if k in tracked_hexes else now_ts - 300)
    ]
    for k in stale_keys:
        del _flight_trails[k]

    # Enforce cap
    if len(_flight_trails) > _MAX_TRACKED_TRAILS:
        sorted_keys = sorted(
            _flight_trails, key=lambda k: _flight_trails[k]["last_seen"]
        )
        evict_count = len(_flight_trails) - _MAX_TRACKED_TRAILS
        for k in sorted_keys[:evict_count]:
            del _flight_trails[k]

    return len(stale_keys)


# ---------------------------------------------------------------------------
# GPS jamming detection (NACp grid analysis)
# ---------------------------------------------------------------------------

def _detect_gps_jamming(flights: list[dict]) -> list[dict]:
    """Analyse NACp values on a 1-degree grid to find GPS interference zones."""
    jamming_grid: dict[str, dict[str, int]] = {}

    for f in flights:
        lat = f.get("lat")
        lng = f.get("lng") or f.get("lon")
        if lat is None or lng is None:
            continue
        nacp = f.get("nac_p")
        if nacp is None:
            continue

        grid_key = f"{int(lat)},{int(lng)}"
        cell = jamming_grid.setdefault(grid_key, {"degraded": 0, "total": 0})
        cell["total"] += 1
        if nacp < 8:
            cell["degraded"] += 1

    zones: list[dict] = []
    for gk, counts in jamming_grid.items():
        if counts["total"] < 3:
            continue
        ratio = counts["degraded"] / counts["total"]
        if ratio > 0.25:
            lat_i, lng_i = gk.split(",")
            severity = "low" if ratio < 0.5 else "medium" if ratio < 0.75 else "high"
            zones.append({
                "lat": int(lat_i) + 0.5,
                "lng": int(lng_i) + 0.5,
                "severity": severity,
                "ratio": round(ratio, 2),
                "degraded": counts["degraded"],
                "total": counts["total"],
            })

    if zones:
        logger.info("gps_jamming.detected", zones=len(zones))
    return zones


# ---------------------------------------------------------------------------
# Holding pattern detection (bearing delta analysis)
# ---------------------------------------------------------------------------

def _detect_holding_patterns(flight_lists: list[list[dict]]) -> int:
    """Tag flights whose recent trail shows >300 deg total turn (circling).

    Returns count of aircraft in holding patterns.
    """
    trails_snapshot = {k: v.get("points", [])[:] for k, v in _flight_trails.items()}
    holding_count = 0

    for flist in flight_lists:
        for f in flist:
            hex_id = f.get("icao24", "").lower()
            trail = trails_snapshot.get(hex_id, [])
            if len(trail) < 6:
                f["holding"] = False
                continue

            pts = trail[-8:]
            total_turn = 0.0
            prev_bearing = 0.0

            for i in range(1, len(pts)):
                lat1 = math.radians(pts[i - 1][0])
                lng1 = math.radians(pts[i - 1][1])
                lat2 = math.radians(pts[i][0])
                lng2 = math.radians(pts[i][1])
                dlng = lng2 - lng1
                x = math.sin(dlng) * math.cos(lat2)
                y = (
                    math.cos(lat1) * math.sin(lat2)
                    - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
                )
                bearing = math.degrees(math.atan2(x, y)) % 360
                if i > 1:
                    delta = abs(bearing - prev_bearing)
                    if delta > 180:
                        delta = 360 - delta
                    total_turn += delta
                prev_bearing = bearing

            f["holding"] = total_turn > 300
            if f["holding"]:
                holding_count += 1

    if holding_count:
        logger.info("holding_patterns.detected", count=holding_count)
    return holding_count


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def fetch_all_flights(
    previous: dict[str, list[dict]] | None = None,
) -> dict[str, list[dict]]:
    """Two-phase ADS-B flight fetching pipeline.

    Parameters
    ----------
    previous:
        Previous result dict (for smart-merge protection against partial
        API failures).  Pass ``None`` on the first call.

    Returns
    -------
    dict with keys: ``commercial_flights``, ``private_jets``,
    ``private_flights``, ``tracked_flights``, ``gps_jamming``.
    """
    if previous is None:
        previous = {}

    # ── Phase 1: adsb.lol fast parallel fetch ────────────────────────────
    adsb_flights = await _fetch_adsb_lol_all_regions()
    logger.info("adsb_lol.fetched", count=len(adsb_flights))

    if not adsb_flights:
        logger.warning("adsb_lol.empty", msg="0 aircraft returned — keeping previous data")
        return previous

    # ── Phase 2: OpenSky + supplemental gap-fill (15s max) ─────────────
    seen_hex: set[str] = set()
    for f in adsb_flights:
        h = f.get("hex")
        if h:
            seen_hex.add(h.lower().strip())

    all_raw = list(adsb_flights)

    async def _gap_fill():
        nonlocal all_raw
        opensky_task = asyncio.create_task(_fetch_opensky_gap_fill(seen_hex))
        supplemental_task = asyncio.create_task(_fetch_supplemental_sources(seen_hex))

        opensky_extra = await opensky_task
        for f in opensky_extra:
            h = f.get("hex", "").lower().strip()
            if h and h not in seen_hex:
                all_raw.append(f)
                seen_hex.add(h)

        supplemental_extra = await supplemental_task
        for f in supplemental_extra:
            h = f.get("hex", "").lower().strip()
            if h and h not in seen_hex:
                all_raw.append(f)
                seen_hex.add(h)

        if opensky_extra or supplemental_extra:
            logger.info("gap_fill.done", opensky=len(opensky_extra), supplemental=len(supplemental_extra))

    try:
        await asyncio.wait_for(_gap_fill(), timeout=10.0)
    except asyncio.TimeoutError:
        logger.debug("gap_fill.timeout", msg="Gap-fill timed out — using adsb.lol data only")
    except Exception as exc:
        logger.debug("gap_fill.error", error=str(exc))

    # ── Route enrichment (5s max, skip if slow) ──────────────────────────
    try:
        await asyncio.wait_for(_fetch_routes(all_raw), timeout=5.0)
    except (asyncio.TimeoutError, Exception):
        pass  # Use cached routes

    # ── Normalize ────────────────────────────────────────────────────────
    flights: list[dict] = []
    for raw in all_raw:
        try:
            normed = _normalize_flight(raw)
            if normed is not None:
                flights.append(normed)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            logger.error("normalize.error", error=str(exc))

    # ── Classify ─────────────────────────────────────────────────────────
    commercial, private_jets, private_ga, tracked = _classify_flights(flights)

    # ── Smart merge (protect against >50 % drop) ─────────────────────────
    prev_commercial = previous.get("commercial_flights", [])
    prev_jets = previous.get("private_jets", [])
    prev_ga = previous.get("private_flights", [])
    prev_total = len(prev_commercial) + len(prev_jets) + len(prev_ga)
    new_total = len(commercial) + len(private_jets) + len(private_ga)

    now = time.time()

    if new_total == 0:
        logger.warning("classify.empty", msg="No civilian flights — keeping previous data")
        commercial = prev_commercial
        private_jets = prev_jets
        private_ga = prev_ga
    elif prev_total > 100 and new_total < prev_total * 0.5:
        logger.warning(
            "classify.drop_detected",
            prev=prev_total,
            new=new_total,
            msg="Keeping previous data to prevent flicker",
        )
        commercial = prev_commercial
        private_jets = prev_jets
        private_ga = prev_ga
    else:
        commercial = _smart_merge(commercial, prev_commercial, now)
        private_jets = _smart_merge(private_jets, prev_jets, now)
        private_ga = _smart_merge(private_ga, prev_ga, now)

    # ── Merge tracked flights with previous tracked ──────────────────────
    prev_tracked = previous.get("tracked_flights", [])
    fresh_tracked_map = {t.get("icao24", "").upper(): t for t in tracked if t.get("icao24")}

    merged_tracked: list[dict] = []
    seen_icaos: set[str] = set()

    for old_t in prev_tracked:
        icao = old_t.get("icao24", "").upper()
        if icao in fresh_tracked_map:
            fresh = fresh_tracked_map[icao]
            for key in ("alert_category", "alert_operator", "alert_special", "alert_flag"):
                if key in old_t and key not in fresh:
                    fresh[key] = old_t[key]
            merged_tracked.append(fresh)
            seen_icaos.add(icao)
        else:
            merged_tracked.append(old_t)
            seen_icaos.add(icao)

    for icao, t in fresh_tracked_map.items():
        if icao not in seen_icaos:
            merged_tracked.append(t)

    logger.info(
        "tracked.merged",
        total=len(merged_tracked),
        fresh=len(fresh_tracked_map),
    )

    # ── Trail accumulation ───────────────────────────────────────────────
    now_ts = datetime.now(timezone.utc).timestamp()
    all_lists = [commercial, private_jets, private_ga, merged_tracked]
    trail_count = _accumulate_trails(all_lists, now_ts, check_route=True)

    tracked_hexes = {t.get("icao24", "").lower() for t in merged_tracked}
    pruned = _prune_trails(now_ts, tracked_hexes)

    logger.info(
        "trails.updated",
        active=trail_count,
        pruned=pruned,
        cache_size=len(_flight_trails),
    )

    # ── GPS jamming detection ────────────────────────────────────────────
    try:
        gps_jamming = _detect_gps_jamming(flights)
    except (ValueError, TypeError, KeyError, ZeroDivisionError) as exc:
        logger.error("gps_jamming.error", error=str(exc))
        gps_jamming = []

    # ── Holding pattern detection ────────────────────────────────────────
    try:
        _detect_holding_patterns(all_lists)
    except (ValueError, TypeError, KeyError, ZeroDivisionError) as exc:
        logger.error("holding_patterns.error", error=str(exc))

    return {
        "commercial_flights": commercial,
        "private_jets": private_jets,
        "private_flights": private_ga,
        "tracked_flights": merged_tracked,
        "gps_jamming": gps_jamming,
    }
