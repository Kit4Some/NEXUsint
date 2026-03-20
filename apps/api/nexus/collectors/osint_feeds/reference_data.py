"""Reference-data loaders -- airports, military bases, datacenters, power plants.

Ported from Shadowbroker ``services/fetchers/geo.py`` and parts of
``services/fetchers/infrastructure.py`` to the NEXUS async / structlog
conventions.  Static JSON files are loaded lazily on first call and cached
for the lifetime of the worker process.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import structlog

from nexus.utils.http_client import fetch_text

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR: Path = Path(__file__).resolve().parents[2] / "data"

_MILITARY_BASES_PATH = _DATA_DIR / "military_bases.json"
_DATACENTERS_PATH = _DATA_DIR / "datacenters_geocoded.json"
_POWER_PLANTS_PATH = _DATA_DIR / "power_plants.json"

# ---------------------------------------------------------------------------
# Lazy-loaded caches (populated on first call, never mutated afterward)
# ---------------------------------------------------------------------------

_military_bases_cache: list[dict] | None = None
_datacenters_cache: list[dict] | None = None
_power_plants_cache: list[dict] | None = None

# ---------------------------------------------------------------------------
# Airports (OurAirports CSV -- fetched once from the web)
# ---------------------------------------------------------------------------

_AIRPORTS_CSV_URL = "https://ourairports.com/data/airports.csv"


async def fetch_airports() -> list[dict]:
    """Download the OurAirports CSV and return large-airport entries.

    Each dict contains:
        name, iata, icao, lat, lng, type, country
    """
    try:
        text = await fetch_text(_AIRPORTS_CSV_URL, timeout=20)
    except Exception as exc:
        logger.error("reference.airports_fetch_failed", error=str(exc))
        return []

    airports: list[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if row.get("type") != "large_airport":
            continue
        iata = row.get("iata_code", "").strip()
        if not iata:
            continue
        try:
            lat = float(row["latitude_deg"])
            lng = float(row["longitude_deg"])
        except (KeyError, ValueError):
            continue

        airports.append({
            "name": row.get("name", ""),
            "iata": iata,
            "icao": row.get("ident", ""),
            "lat": lat,
            "lng": lng,
            "type": row.get("type", "large_airport"),
            "country": row.get("iso_country", ""),
        })

    logger.info("reference.airports_loaded", count=len(airports))
    return airports


# ---------------------------------------------------------------------------
# Static JSON loaders (sync, lazy-cached)
# ---------------------------------------------------------------------------


def _load_json_file(path: Path) -> list[dict]:
    """Read a JSON array from *path*, filtering entries without valid coords."""
    if not path.exists():
        logger.warning("reference.file_not_found", path=str(path))
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    valid: list[dict] = []
    for entry in raw:
        lat = entry.get("lat")
        lng = entry.get("lng")
        if lat is None or lng is None:
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue
        valid.append(entry)
    return valid


def load_military_bases() -> list[dict]:
    """Load military base locations from ``apps/api/data/military_bases.json``.

    Each dict contains at minimum: name, country, lat, lng.
    Results are cached after the first call.
    """
    global _military_bases_cache
    if _military_bases_cache is not None:
        return _military_bases_cache

    entries = _load_json_file(_MILITARY_BASES_PATH)
    bases = [
        {
            "name": e.get("name", "Unknown"),
            "country": e.get("country", ""),
            "operator": e.get("operator", ""),
            "branch": e.get("branch", ""),
            "lat": e["lat"],
            "lng": e["lng"],
        }
        for e in entries
    ]
    _military_bases_cache = bases
    logger.info("reference.military_bases_loaded", count=len(bases))
    return bases


def load_datacenters() -> list[dict]:
    """Load datacenter locations from ``apps/api/data/datacenters_geocoded.json``.

    Each dict contains at minimum: name, company, city, country, lat, lng.
    Results are cached after the first call.
    """
    global _datacenters_cache
    if _datacenters_cache is not None:
        return _datacenters_cache

    entries = _load_json_file(_DATACENTERS_PATH)
    dcs = [
        {
            "name": e.get("name", "Unknown"),
            "company": e.get("company", ""),
            "street": e.get("street", ""),
            "city": e.get("city", ""),
            "country": e.get("country", ""),
            "lat": e["lat"],
            "lng": e["lng"],
        }
        for e in entries
    ]
    _datacenters_cache = dcs
    logger.info("reference.datacenters_loaded", count=len(dcs))
    return dcs


def load_power_plants() -> list[dict]:
    """Load power-plant locations from ``apps/api/data/power_plants.json``.

    Each dict contains at minimum: name, country, fuel_type, capacity_mw, lat, lng.
    Results are cached after the first call.
    """
    global _power_plants_cache
    if _power_plants_cache is not None:
        return _power_plants_cache

    entries = _load_json_file(_POWER_PLANTS_PATH)
    plants = [
        {
            "name": e.get("name", "Unknown"),
            "country": e.get("country", ""),
            "fuel_type": e.get("fuel_type", "Unknown"),
            "capacity_mw": e.get("capacity_mw"),
            "owner": e.get("owner", ""),
            "lat": e["lat"],
            "lng": e["lng"],
        }
        for e in entries
    ]
    _power_plants_cache = plants
    logger.info("reference.power_plants_loaded", count=len(plants))
    return plants
