"""Infrastructure OSINT feeds -- internet outages (IODA) and KiwiSDR receivers.

Ported from Shadowbroker ``services/fetchers/infrastructure.py`` and
``services/kiwisdr_fetcher.py`` to the NEXUS async / structlog conventions.
"""

from __future__ import annotations

import heapq
import re
import time

import structlog

from nexus.utils.http_client import fetch_json, fetch_text

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IODA_BASE = "https://api.ioda.inetintel.cc.gatech.edu/v2"
_RELIABLE_DATASOURCES = {"bgp", "ping-slash24"}
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_KIWISDR_PUBLIC_URL = "http://rx.linkfanel.net/.public/"

# Simple in-memory geocode cache (region name -> (lat, lng) | None).
# Intentionally *not* module-level mutable state shared across requests --
# it is a plain dict acting as a warm cache across calls within the same
# worker process.
_region_geocode_cache: dict[str, tuple[float, float] | None] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _geocode_region(region_name: str, country_name: str) -> tuple[float, float] | None:
    """Geocode a region via Nominatim (cached per worker lifetime)."""
    cache_key = f"{region_name}|{country_name}"
    if cache_key in _region_geocode_cache:
        return _region_geocode_cache[cache_key]

    try:
        import urllib.parse

        query = urllib.parse.quote(f"{region_name}, {country_name}")
        url = f"{_NOMINATIM_URL}?q={query}&format=json&limit=1"
        results = await fetch_json(url, timeout=8, retries=1)
        if results and isinstance(results, list):
            lat = float(results[0]["lat"])
            lng = float(results[0]["lon"])
            _region_geocode_cache[cache_key] = (lat, lng)
            return (lat, lng)
    except Exception:
        logger.debug("infrastructure.geocode_failed", region=region_name)

    _region_geocode_cache[cache_key] = None
    return None


# ---------------------------------------------------------------------------
# Internet Outages (IODA -- Georgia Tech)
# ---------------------------------------------------------------------------


async def fetch_internet_outages() -> list[dict]:
    """Fetch regional internet outage alerts from IODA (last 24 h).

    Returns a list of dicts, each with keys:
        country, region, score, lat, lng
    sorted by severity descending (up to 100 entries).
    """
    now = int(time.time())
    start = now - 86400
    url = f"{_IODA_BASE}/outages/alerts?from={start}&until={now}&limit=500"

    try:
        data = await fetch_json(url, timeout=15, retries=1)
    except Exception as exc:
        logger.error("infrastructure.ioda_fetch_failed", error=str(exc))
        return []

    alerts = data.get("data", []) if isinstance(data, dict) else []

    # De-duplicate by region, keeping the highest-severity alert per region.
    region_outages: dict[str, dict] = {}

    for alert in alerts:
        entity = alert.get("entity", {})
        if entity.get("type") != "region":
            continue
        if alert.get("level") == "normal":
            continue
        if alert.get("datasource", "") not in _RELIABLE_DATASOURCES:
            continue

        code = entity.get("code", "")
        attrs = entity.get("attrs", {})

        value = alert.get("value", 0)
        history_value = alert.get("historyValue", 0)
        severity = 0
        if history_value and history_value > 0:
            severity = round((1 - value / history_value) * 100)
        severity = max(0, min(severity, 100))
        if severity < 10:
            continue

        if code not in region_outages or severity > region_outages[code]["score"]:
            region_outages[code] = {
                "country": attrs.get("country_name", ""),
                "region": entity.get("name", ""),
                "score": severity,
                "country_code": attrs.get("country_code", ""),
                "_region_name": entity.get("name", ""),
                "_country_name": attrs.get("country_name", ""),
            }

    # Geocode each region and attach lat/lng.
    geocoded: list[dict] = []
    for entry in region_outages.values():
        coords = await _geocode_region(entry.pop("_region_name"), entry.pop("_country_name"))
        if coords:
            entry["lat"] = coords[0]
            entry["lng"] = coords[1]
            geocoded.append(entry)

    outages = heapq.nlargest(100, geocoded, key=lambda x: x["score"])
    logger.info("infrastructure.internet_outages", count=len(outages))
    return outages


# ---------------------------------------------------------------------------
# KiwiSDR / WebSDR Receivers
# ---------------------------------------------------------------------------

# Regex helpers matching HTML-comment metadata inside KiwiSDR entry divs.
_RE_COMMENT = re.compile(r"<!--\s*{field}=(.*?)\s*-->")
_RE_GPS = re.compile(r"<!--\s*gps=\(([^,]+),\s*([^)]+)\)\s*-->")
_RE_HREF = re.compile(r"href='(https?://[^']+)'")
_RE_ENTRY = re.compile(r"<div class='cl-entry[^']*'>(.*?)</div>\s*</div>", re.DOTALL)


def _parse_comment(html: str, field: str) -> str:
    """Extract ``field`` from ``<!-- field=value -->``."""
    m = re.search(rf"<!--\s*{field}=(.*?)\s*-->", html)
    return m.group(1).strip() if m else ""


def _parse_gps(html: str) -> tuple[float | None, float | None]:
    m = _RE_GPS.search(html)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            return None, None
    return None, None


async def fetch_kiwisdr() -> list[dict]:
    """Fetch online KiwiSDR / WebSDR receiver locations.

    Returns a list of dicts, each with keys:
        name, lat, lng, url, bands, users
    """
    try:
        html = await fetch_text(_KIWISDR_PUBLIC_URL, timeout=20)
    except Exception as exc:
        logger.error("infrastructure.kiwisdr_fetch_failed", error=str(exc))
        return []

    entries = _RE_ENTRY.findall(html)
    nodes: list[dict] = []

    for entry in entries:
        lat, lon = _parse_gps(entry)
        if lat is None or lon is None:
            continue
        if abs(lat) > 90 or abs(lon) > 180:
            continue

        if _parse_comment(entry, "offline") == "yes":
            continue

        name = _parse_comment(entry, "name") or "Unknown SDR"
        users_str = _parse_comment(entry, "users")
        bands = _parse_comment(entry, "bands")

        url_match = _RE_HREF.search(entry)
        url = url_match.group(1) if url_match else ""

        try:
            users = int(users_str) if users_str else 0
        except ValueError:
            users = 0

        nodes.append({
            "name": name[:120],
            "lat": round(lat, 5),
            "lng": round(lon, 5),
            "url": url,
            "bands": bands,
            "users": users,
        })

    logger.info("infrastructure.kiwisdr", count=len(nodes))
    return nodes
