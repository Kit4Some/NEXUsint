"""Satellite tracking -- CelesTrak TLE fetch, SGP4 propagation, intel classification.

Ported from Shadowbroker satellites.py to async NEXUS patterns.

CelesTrak Fair Use Policy (https://celestrak.org/NORAD/elements/):
  - Do NOT request the same data more than once every 24 hours
  - Use If-Modified-Since headers for conditional requests
  - No parallel/concurrent connections -- one request at a time
  - Set a descriptive User-Agent
"""

from __future__ import annotations

import json
import math
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import structlog
from sgp4.api import Satrec, jday
from sgp4.earth_gravity import wgs84

from nexus.utils.http_client import fetch_json, fetch_text

logger = structlog.get_logger("nexus.collectors.osint_feeds.satellites")

# ---------------------------------------------------------------------------
# Cache paths and freshness tracking
# ---------------------------------------------------------------------------

_SAT_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "sat_gp_cache.json"
_CELESTRAK_FETCH_INTERVAL = 86400  # 24 hours (CelesTrak fair use)

_tle_cache: list[dict] | None = None
_tle_last_fetch: float = 0.0

# ---------------------------------------------------------------------------
# Intel classification database
# ---------------------------------------------------------------------------

_SAT_INTEL_DB: list[tuple[str, dict]] = [
    # Military reconnaissance
    ("USA 224", {"country": "USA", "mission": "military_recon", "sat_type": "KH-11 Reconnaissance"}),
    ("USA 245", {"country": "USA", "mission": "military_recon", "sat_type": "KH-11 Reconnaissance"}),
    ("USA 290", {"country": "USA", "mission": "military_recon", "sat_type": "KH-11 Reconnaissance"}),
    ("USA 314", {"country": "USA", "mission": "military_recon", "sat_type": "KH-11 Reconnaissance"}),
    ("USA 338", {"country": "USA", "mission": "military_recon", "sat_type": "Keyhole Successor"}),
    ("TOPAZ", {"country": "Russia", "mission": "military_recon", "sat_type": "Optical Reconnaissance"}),
    ("PERSONA", {"country": "Russia", "mission": "military_recon", "sat_type": "Optical Reconnaissance"}),
    ("KONDOR", {"country": "Russia", "mission": "military_sar", "sat_type": "SAR Reconnaissance"}),
    ("BARS-M", {"country": "Russia", "mission": "military_recon", "sat_type": "Mapping Reconnaissance"}),
    ("YAOGAN", {"country": "China", "mission": "military_recon", "sat_type": "Remote Sensing / ELINT"}),
    ("GAOFEN", {"country": "China", "mission": "military_recon", "sat_type": "High-Res Imaging"}),
    ("JILIN", {"country": "China", "mission": "commercial_imaging", "sat_type": "Video / Imaging"}),
    ("OFEK", {"country": "Israel", "mission": "military_recon", "sat_type": "Reconnaissance"}),
    ("CSO", {"country": "France", "mission": "military_recon", "sat_type": "Optical Reconnaissance"}),
    ("IGS", {"country": "Japan", "mission": "military_recon", "sat_type": "Intelligence Gathering"}),
    # SAR imaging
    ("CAPELLA", {"country": "USA", "mission": "sar", "sat_type": "SAR Imaging"}),
    ("ICEYE", {"country": "Finland", "mission": "sar", "sat_type": "SAR Microsatellite"}),
    ("COSMO-SKYMED", {"country": "Italy", "mission": "sar", "sat_type": "SAR Constellation"}),
    ("TANDEM", {"country": "Germany", "mission": "sar", "sat_type": "SAR Interferometry"}),
    ("PAZ", {"country": "Spain", "mission": "sar", "sat_type": "SAR Imaging"}),
    # Commercial imaging
    ("WORLDVIEW", {"country": "USA", "mission": "commercial_imaging", "sat_type": "Maxar High-Res"}),
    ("GEOEYE", {"country": "USA", "mission": "commercial_imaging", "sat_type": "Maxar Imaging"}),
    ("PLEIADES", {"country": "France", "mission": "commercial_imaging", "sat_type": "Airbus Imaging"}),
    ("SPOT", {"country": "France", "mission": "commercial_imaging", "sat_type": "Airbus Medium-Res"}),
    ("PLANET", {"country": "USA", "mission": "commercial_imaging", "sat_type": "PlanetScope"}),
    ("SKYSAT", {"country": "USA", "mission": "commercial_imaging", "sat_type": "Planet Video"}),
    ("BLACKSKY", {"country": "USA", "mission": "commercial_imaging", "sat_type": "BlackSky Imaging"}),
    # SIGINT
    ("NROL", {"country": "USA", "mission": "sigint", "sat_type": "Classified NRO"}),
    ("MENTOR", {"country": "USA", "mission": "sigint", "sat_type": "SIGINT / ELINT"}),
    ("LUCH", {"country": "Russia", "mission": "sigint", "sat_type": "Relay / SIGINT"}),
    ("SHIJIAN", {"country": "China", "mission": "sigint", "sat_type": "ELINT / Tech Demo"}),
    # Navigation
    ("NAVSTAR", {"country": "USA", "mission": "navigation", "sat_type": "GPS"}),
    ("GLONASS", {"country": "Russia", "mission": "navigation", "sat_type": "GLONASS"}),
    ("BEIDOU", {"country": "China", "mission": "navigation", "sat_type": "BeiDou"}),
    ("GALILEO", {"country": "EU", "mission": "navigation", "sat_type": "Galileo"}),
    # Early warning
    ("SBIRS", {"country": "USA", "mission": "early_warning", "sat_type": "Missile Warning"}),
    ("TUNDRA", {"country": "Russia", "mission": "early_warning", "sat_type": "Missile Warning"}),
    # Space stations
    ("ISS", {"country": "Intl", "mission": "space_station", "sat_type": "Space Station"}),
    ("TIANGONG", {"country": "China", "mission": "space_station", "sat_type": "Space Station"}),
]

# Mission -> user-friendly category label
_CATEGORY_MAP: dict[str, str] = {
    "military_recon": "intelligence",
    "military_sar": "intelligence",
    "sar": "intelligence",
    "commercial_imaging": "imaging",
    "sigint": "intelligence",
    "navigation": "navigation",
    "early_warning": "early_warning",
    "space_station": "space_station",
}


# ---------------------------------------------------------------------------
# GMST helper
# ---------------------------------------------------------------------------

def _gmst(jd_ut1: float) -> float:
    """Greenwich Mean Sidereal Time in radians from Julian Date."""
    t = (jd_ut1 - 2451545.0) / 36525.0
    gmst_sec = (
        67310.54841
        + (876600.0 * 3600 + 8640184.812866) * t
        + 0.093104 * t * t
        - 6.2e-6 * t * t * t
    )
    return (gmst_sec % 86400) / 86400.0 * 2 * math.pi


# ---------------------------------------------------------------------------
# Disk cache helpers
# ---------------------------------------------------------------------------

def _load_sat_cache() -> list[dict] | None:
    """Load satellite GP data from local disk cache (if < 48h old)."""
    try:
        if not _SAT_CACHE_PATH.exists():
            return None
        import os

        age_hours = (time.time() - os.path.getmtime(str(_SAT_CACHE_PATH))) / 3600
        if age_hours >= 48:
            logger.info("satellites.disk_cache_stale", age_hours=round(age_hours, 1))
            return None
        with open(_SAT_CACHE_PATH, "r") as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 10:
            logger.info("satellites.disk_cache_loaded", count=len(data), age_hours=round(age_hours, 1))
            return data
    except (IOError, OSError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("satellites.disk_cache_load_failed", error=str(exc))
    return None


def _save_sat_cache(data: list[dict]) -> None:
    """Persist satellite GP data to local disk cache."""
    try:
        _SAT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_SAT_CACHE_PATH, "w") as f:
            json.dump(data, f)
        logger.info("satellites.disk_cache_saved", count=len(data))
    except (IOError, OSError) as exc:
        logger.warning("satellites.disk_cache_save_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _classify_satellites(gp_data: list[dict]) -> list[dict]:
    """Filter GP catalog to intel-relevant satellites and attach metadata."""
    classified: list[dict] = []
    for sat in gp_data:
        name = sat.get("OBJECT_NAME", "UNKNOWN").upper()
        intel: dict | None = None
        for key, meta in _SAT_INTEL_DB:
            if key.upper() in name:
                intel = dict(meta)
                break
        if intel is None:
            continue
        entry = {
            "norad_id": sat.get("NORAD_CAT_ID"),
            "name": sat.get("OBJECT_NAME", "UNKNOWN"),
            "MEAN_MOTION": sat.get("MEAN_MOTION"),
            "ECCENTRICITY": sat.get("ECCENTRICITY"),
            "INCLINATION": sat.get("INCLINATION"),
            "RA_OF_ASC_NODE": sat.get("RA_OF_ASC_NODE"),
            "ARG_OF_PERICENTER": sat.get("ARG_OF_PERICENTER"),
            "MEAN_ANOMALY": sat.get("MEAN_ANOMALY"),
            "BSTAR": sat.get("BSTAR"),
            "EPOCH": sat.get("EPOCH"),
        }
        entry.update(intel)
        classified.append(entry)
    logger.info("satellites.classified", classified=len(classified), catalog_total=len(gp_data))
    return classified


# ---------------------------------------------------------------------------
# SGP4 propagation
# ---------------------------------------------------------------------------

def _propagate(classified: list[dict]) -> list[dict]:
    """Run SGP4 propagation on classified satellites and return positioned dicts."""
    now = datetime.utcnow()
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6)

    results: list[dict] = []
    for s in classified:
        try:
            mean_motion = s.get("MEAN_MOTION")
            ecc = s.get("ECCENTRICITY")
            incl = s.get("INCLINATION")
            raan = s.get("RA_OF_ASC_NODE")
            argp = s.get("ARG_OF_PERICENTER")
            ma = s.get("MEAN_ANOMALY")
            bstar = s.get("BSTAR", 0)
            epoch_str = s.get("EPOCH")
            norad_id = s.get("norad_id", 0)

            if mean_motion is None or ecc is None or incl is None:
                continue

            epoch_dt = datetime.strptime(epoch_str[:19], "%Y-%m-%dT%H:%M:%S")
            epoch_jd, epoch_fr = jday(
                epoch_dt.year, epoch_dt.month, epoch_dt.day,
                epoch_dt.hour, epoch_dt.minute, epoch_dt.second,
            )

            sat_obj = Satrec()
            sat_obj.sgp4init(
                wgs84, "i", norad_id,
                (epoch_jd + epoch_fr) - 2433281.5,
                bstar, 0.0, 0.0, ecc,
                math.radians(argp), math.radians(incl),
                math.radians(ma),
                mean_motion * 2 * math.pi / 1440.0,
                math.radians(raan),
            )

            e, r, _v = sat_obj.sgp4(jd, fr)
            if e != 0:
                continue

            x, y, z = r
            gmst = _gmst(jd + fr)
            lng_rad = math.atan2(y, x) - gmst
            lat_rad = math.atan2(z, math.sqrt(x * x + y * y))
            alt_km = math.sqrt(x * x + y * y + z * z) - 6371.0

            lat = round(math.degrees(lat_rad), 4)
            lng_deg = math.degrees(lng_rad) % 360
            lng = round(lng_deg - 360 if lng_deg > 180 else lng_deg, 4)

            category = _CATEGORY_MAP.get(s.get("mission", ""), "other")
            country = s.get("country", "Unknown")

            # Build the wiki link for USA-designated satellites
            sat_name = s.get("name", "")
            wiki = s.get("wiki")
            if not wiki:
                usa_match = re.search(r"USA[\s\-]*(\d+)", sat_name)
                if usa_match:
                    wiki = f"https://en.wikipedia.org/wiki/USA-{usa_match.group(1)}"

            result: dict = {
                "name": sat_name,
                "lat": lat,
                "lng": lng,
                "alt": round(alt_km, 1),
                "type": s.get("sat_type", "Unknown"),
                "norad_id": norad_id,
                "category": category,
                "country": country,
            }
            if wiki:
                result["wiki"] = wiki

            results.append(result)
        except (ValueError, TypeError, KeyError, AttributeError, ZeroDivisionError):
            continue

    return results


# ---------------------------------------------------------------------------
# CelesTrak GP fetch (primary source)
# ---------------------------------------------------------------------------

async def _fetch_celestrak_gp() -> list[dict] | None:
    """Download active-satellite GP records from CelesTrak (JSON format)."""
    urls = [
        "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json",
        "https://celestrak.com/NORAD/elements/gp.php?GROUP=active&FORMAT=json",
    ]
    for url in urls:
        try:
            data = await fetch_json(url, timeout=20, retries=1)
            if isinstance(data, list) and len(data) > 100:
                logger.info("satellites.celestrak_ok", count=len(data))
                return data
        except Exception as exc:
            logger.warning("satellites.celestrak_failed", url=url, error=str(exc))
    return None


# ---------------------------------------------------------------------------
# TLE fallback API
# ---------------------------------------------------------------------------

async def _fetch_tle_fallback() -> list[dict]:
    """Fetch TLEs from tle.ivanstanojevic.me when CelesTrak is unreachable."""
    search_terms: set[str] = set()
    for key, _ in _SAT_INTEL_DB:
        parts = key.split()
        term = parts[0] if len(parts) > 1 and parts[0] in ("USA", "NROL") else key
        search_terms.add(term)

    all_results: list[dict] = []
    seen_ids: set[int] = set()

    for term in search_terms:
        try:
            url = f"https://tle.ivanstanojevic.me/api/tle/?search={term}&page_size=100&format=json"
            data = await fetch_json(url, timeout=10, retries=1)
            for member in data.get("member", []):
                gp = _parse_tle_to_gp(
                    member.get("name", "UNKNOWN"),
                    member.get("satelliteId"),
                    member.get("line1", ""),
                    member.get("line2", ""),
                )
                if gp:
                    sat_id = gp.get("NORAD_CAT_ID")
                    if sat_id not in seen_ids:
                        seen_ids.add(sat_id)
                        all_results.append(gp)
        except Exception as exc:
            logger.debug("satellites.tle_fallback_search_failed", term=term, error=str(exc))

    logger.info("satellites.tle_fallback_done", count=len(all_results))
    return all_results


def _parse_tle_to_gp(name: str, norad_id: int | None, line1: str, line2: str) -> dict | None:
    """Convert a TLE two-line element set to CelesTrak GP-style dict."""
    try:
        incl = float(line2[8:16].strip())
        raan = float(line2[17:25].strip())
        ecc = float("0." + line2[26:33].strip())
        argp = float(line2[34:42].strip())
        ma = float(line2[43:51].strip())
        mm = float(line2[52:63].strip())
        bstar_str = line1[53:61].strip()
        if bstar_str:
            mantissa = float(bstar_str[:-2]) / 1e5
            exponent = int(bstar_str[-2:])
            bstar = mantissa * (10**exponent)
        else:
            bstar = 0.0
        epoch_yr = int(line1[18:20])
        epoch_day = float(line1[20:32].strip())
        year = 2000 + epoch_yr if epoch_yr < 57 else 1900 + epoch_yr
        epoch_dt = datetime(year, 1, 1) + timedelta(days=epoch_day - 1)
        return {
            "OBJECT_NAME": name,
            "NORAD_CAT_ID": norad_id,
            "MEAN_MOTION": mm,
            "ECCENTRICITY": ecc,
            "INCLINATION": incl,
            "RA_OF_ASC_NODE": raan,
            "ARG_OF_PERICENTER": argp,
            "MEAN_ANOMALY": ma,
            "BSTAR": bstar,
            "EPOCH": epoch_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    except (ValueError, TypeError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_satellites() -> list[dict]:
    """Fetch intel-classified satellites with real-time SGP4 positions.

    Returns a list of dicts, each with keys:
        name, lat, lng, alt, type, norad_id, category, country
    """
    global _tle_cache, _tle_last_fetch

    now_ts = time.time()

    # Refresh GP data if cache is stale (>24h)
    if _tle_cache is None or (now_ts - _tle_last_fetch) > _CELESTRAK_FETCH_INTERVAL:
        gp_data = await _fetch_celestrak_gp()

        if gp_data:
            _tle_cache = gp_data
            _tle_last_fetch = now_ts
            _save_sat_cache(gp_data)
        else:
            # CelesTrak unreachable -- try TLE fallback API
            logger.info("satellites.trying_tle_fallback")
            fallback = await _fetch_tle_fallback()
            if fallback and len(fallback) > 10:
                _tle_cache = fallback
                _tle_last_fetch = now_ts
                _save_sat_cache(fallback)

        # Last resort: load from disk
        if _tle_cache is None:
            disk = _load_sat_cache()
            if disk:
                _tle_cache = disk
                # Set fetch time so we retry network in 5 minutes, not 24h
                _tle_last_fetch = now_ts - (_CELESTRAK_FETCH_INTERVAL - 300)

    if not _tle_cache:
        logger.warning("satellites.no_data_available")
        return []

    classified = _classify_satellites(_tle_cache)
    results = _propagate(classified)

    logger.info("satellites.done", classified=len(classified), positioned=len(results))
    return results
