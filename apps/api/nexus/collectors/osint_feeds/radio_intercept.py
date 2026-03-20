"""Radio intercept OSINT feeds -- Broadcastify top feeds and OpenMHz systems.

Ported from Shadowbroker ``services/radio_intercept.py`` to the NEXUS
async / structlog conventions.  HTML parsing uses regex instead of
BeautifulSoup to avoid the extra dependency.
"""

from __future__ import annotations

import math
import re

import structlog

from nexus.utils.http_client import fetch_json, fetch_text

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BROADCASTIFY_TOP_URL = "https://www.broadcastify.com/listen/top"
_OPENMHZ_SYSTEMS_URL = "https://api.openmhz.com/systems"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return great-circle distance in miles between two points."""
    r = 3958.8  # Earth radius in miles
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Broadcastify Top 50
# ---------------------------------------------------------------------------

# Regex that matches each <tr> row inside the feeds table.
_RE_TABLE_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
_RE_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
_RE_HREF = re.compile(r'href=["\']([^"\']+)["\']')


def _strip_tags(html: str) -> str:
    """Remove HTML tags, returning plain text."""
    return re.sub(r"<[^>]+>", "", html).strip()


async def fetch_radio_top() -> list[dict]:
    """Scrape the Broadcastify Top 50 live scanner feeds.

    Returns a list of dicts, each with keys:
        id, name, listeners, location, url
    """
    try:
        html = await fetch_text(
            _BROADCASTIFY_TOP_URL, timeout=10, headers=_BROWSER_HEADERS
        )
    except Exception as exc:
        logger.error("radio.broadcastify_fetch_failed", error=str(exc))
        return []

    # Find the main feeds table (class="btable").
    table_match = re.search(
        r"<table[^>]*class=['\"]btable['\"][^>]*>(.*?)</table>", html, re.DOTALL
    )
    if not table_match:
        logger.warning("radio.broadcastify_table_not_found")
        return []

    table_html = table_match.group(1)
    rows = _RE_TABLE_ROW.findall(table_html)

    feeds: list[dict] = []
    for row in rows:
        cols = _RE_TD.findall(row)
        if len(cols) < 4:
            continue

        listeners_str = _strip_tags(cols[0]).replace(",", "")
        if not listeners_str.isdigit():
            continue  # skip header row
        listeners = int(listeners_str)

        # Column with the feed link (index 2 in Broadcastify layout)
        link_col = cols[2]
        href_match = _RE_HREF.search(link_col)
        if not href_match:
            continue
        href = href_match.group(1)
        if "/listen/feed/" not in href:
            continue
        feed_id = href.rstrip("/").split("/")[-1]

        location = _strip_tags(cols[1])
        name = _strip_tags(cols[2])

        feeds.append({
            "id": feed_id,
            "name": name,
            "listeners": listeners,
            "location": location,
            "url": f"https://broadcastify.cdnstream1.com/{feed_id}",
        })

    logger.info("radio.broadcastify_top", count=len(feeds))
    return feeds


# ---------------------------------------------------------------------------
# OpenMHz Systems
# ---------------------------------------------------------------------------


async def fetch_openmhz_systems() -> list[dict]:
    """Fetch the full directory of OpenMHz trunked radio systems.

    Returns a list of dicts as provided by the OpenMHz API (each entry
    typically contains ``name``, ``shortName``, ``lat``, ``lng``,
    ``description``, etc.).
    """
    try:
        data = await fetch_json(_OPENMHZ_SYSTEMS_URL, timeout=15, retries=2)
    except Exception as exc:
        logger.error("radio.openmhz_fetch_failed", error=str(exc))
        return []

    systems = data.get("systems", []) if isinstance(data, dict) else []
    logger.info("radio.openmhz_systems", count=len(systems))
    return systems


# ---------------------------------------------------------------------------
# Nearest OpenMHz System
# ---------------------------------------------------------------------------


async def fetch_nearest_radio(
    lat: float,
    lng: float,
    limit: int = 5,
) -> list[dict]:
    """Find the nearest OpenMHz trunked radio systems to *lat*/*lng*.

    Each returned dict includes all original OpenMHz fields plus
    ``distance_miles``.
    """
    systems = await fetch_openmhz_systems()
    if not systems:
        return []

    scored: list[dict] = []
    for s in systems:
        s_lat = s.get("lat")
        s_lng = s.get("lng")
        if s_lat is None or s_lng is None:
            continue
        try:
            dist = _haversine(lat, lng, float(s_lat), float(s_lng))
        except (TypeError, ValueError):
            continue
        scored.append({**s, "distance_miles": round(dist, 2)})

    scored.sort(key=lambda x: x["distance_miles"])
    return scored[:limit]
