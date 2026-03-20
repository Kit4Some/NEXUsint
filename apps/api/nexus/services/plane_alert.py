"""Plane-Alert DB -- load and enrich aircraft with tracked metadata.

Ported from Shadowbroker plane_alert.py to NEXUS patterns (structlog, fixed data paths).
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog

logger = structlog.get_logger("nexus.services.plane_alert")

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_PLANE_ALERT_DB_PATH = _DATA_DIR / "plane_alert_db.json"
_TRACKED_NAMES_PATH = _DATA_DIR / "tracked_names.json"

# ---------------------------------------------------------------------------
# Exact category -> color mapping for all 53 known categories.
# O(1) dict lookup -- no keyword scanning, no false positives.
# ---------------------------------------------------------------------------
_CATEGORY_COLOR: dict[str, str] = {
    # YELLOW -- Military / Intelligence / Defense
    "USAF": "yellow",
    "Other Air Forces": "yellow",
    "Toy Soldiers": "yellow",
    "Oxcart": "yellow",
    "United States Navy": "yellow",
    "GAF": "yellow",
    "Hired Gun": "yellow",
    "United States Marine Corps": "yellow",
    "Gunship": "yellow",
    "RAF": "yellow",
    "Other Navies": "yellow",
    "Special Forces": "yellow",
    "Zoomies": "yellow",
    "Royal Navy Fleet Air Arm": "yellow",
    "Army Air Corps": "yellow",
    "Aerobatic Teams": "yellow",
    "UAV": "yellow",
    "Ukraine": "yellow",
    "Nuclear": "yellow",
    # LIME -- Emergency / Medical / Rescue / Fire
    "Flying Doctors": "#32cd32",
    "Aerial Firefighter": "#32cd32",
    "Coastguard": "#32cd32",
    # BLUE -- Government / Law Enforcement / Civil
    "Police Forces": "blue",
    "Governments": "blue",
    "Quango": "blue",
    "UK National Police Air Service": "blue",
    "CAP": "blue",
    # BLACK -- Privacy / PIA
    "PIA": "black",
    # RED -- Dictator / Oligarch
    "Dictator Alert": "red",
    "Da Comrade": "red",
    "Oligarch": "red",
    # HOT PINK -- High Value Assets / VIP / Celebrity
    "Head of State": "#ff1493",
    "Royal Aircraft": "#ff1493",
    "Don't you know who I am?": "#ff1493",
    "As Seen on TV": "#ff1493",
    "Bizjets": "#ff1493",
    "Vanity Plate": "#ff1493",
    "Football": "#ff1493",
    # ORANGE -- Joe Cool
    "Joe Cool": "orange",
    # WHITE -- Climate Crisis
    "Climate Crisis": "white",
    # PURPLE -- General Tracked / Other Notable
    "Historic": "purple",
    "Jump Johnny Jump": "purple",
    "Ptolemy would be proud": "purple",
    "Distinctive": "purple",
    "Dogs with Jobs": "purple",
    "You came here in that thing?": "purple",
    "Big Hello": "purple",
    "Watch Me Fly": "purple",
    "Perfectly Serviceable Aircraft": "purple",
    "Jesus he Knows me": "purple",
    "Gas Bags": "purple",
    "Radiohead": "purple",
}


def _category_to_color(cat: str) -> str:
    """O(1) exact lookup. Unknown categories default to purple."""
    return _CATEGORY_COLOR.get(cat, "purple")


# ---------------------------------------------------------------------------
# POTUS Fleet -- override colors and operator names for presidential aircraft.
# ---------------------------------------------------------------------------
_POTUS_FLEET: dict[str, dict] = {
    "ADFDF8": {"color": "#ff1493", "operator": "Air Force One (82-8000)", "category": "Head of State", "wiki": "Air_Force_One", "fleet": "AF1"},
    "ADFDF9": {"color": "#ff1493", "operator": "Air Force One (92-9000)", "category": "Head of State", "wiki": "Air_Force_One", "fleet": "AF1"},
    "ADFEB7": {"color": "blue", "operator": "Air Force Two (98-0001)", "category": "Governments", "wiki": "Air_Force_Two", "fleet": "AF2"},
    "ADFEB8": {"color": "blue", "operator": "Air Force Two (98-0002)", "category": "Governments", "wiki": "Air_Force_Two", "fleet": "AF2"},
    "ADFEB9": {"color": "blue", "operator": "Air Force Two (99-0003)", "category": "Governments", "wiki": "Air_Force_Two", "fleet": "AF2"},
    "ADFEBA": {"color": "blue", "operator": "Air Force Two (99-0004)", "category": "Governments", "wiki": "Air_Force_Two", "fleet": "AF2"},
    "AE4AE6": {"color": "blue", "operator": "Air Force Two (09-0015)", "category": "Governments", "wiki": "Air_Force_Two", "fleet": "AF2"},
    "AE4AE8": {"color": "blue", "operator": "Air Force Two (09-0016)", "category": "Governments", "wiki": "Air_Force_Two", "fleet": "AF2"},
    "AE4AEA": {"color": "blue", "operator": "Air Force Two (09-0017)", "category": "Governments", "wiki": "Air_Force_Two", "fleet": "AF2"},
    "AE4AEC": {"color": "blue", "operator": "Air Force Two (19-0018)", "category": "Governments", "wiki": "Air_Force_Two", "fleet": "AF2"},
    "AE0865": {"color": "#ff1493", "operator": "Marine One (VH-3D)", "category": "Head of State", "wiki": "Marine_One", "fleet": "M1"},
    "AE5E76": {"color": "#ff1493", "operator": "Marine One (VH-92A)", "category": "Head of State", "wiki": "Marine_One", "fleet": "M1"},
    "AE5E77": {"color": "#ff1493", "operator": "Marine One (VH-92A)", "category": "Head of State", "wiki": "Marine_One", "fleet": "M1"},
    "AE5E79": {"color": "#ff1493", "operator": "Marine One (VH-92A)", "category": "Head of State", "wiki": "Marine_One", "fleet": "M1"},
}

# ---------------------------------------------------------------------------
# In-memory databases (lazy-loaded on first call)
# ---------------------------------------------------------------------------
_plane_alert_db: dict[str, dict] | None = None
_tracked_names_db: dict[str, dict] | None = None


def _get_plane_alert_db() -> dict[str, dict]:
    """Lazy-load plane_alert_db.json into memory on first access."""
    global _plane_alert_db
    if _plane_alert_db is not None:
        return _plane_alert_db

    _plane_alert_db = {}
    if not _PLANE_ALERT_DB_PATH.exists():
        logger.warning("plane_alert_db.json not found", path=str(_PLANE_ALERT_DB_PATH))
        return _plane_alert_db

    try:
        raw: dict = json.loads(_PLANE_ALERT_DB_PATH.read_text(encoding="utf-8"))
        for icao_hex, info in raw.items():
            info["color"] = _category_to_color(info.get("category", ""))
            override = _POTUS_FLEET.get(icao_hex)
            if override:
                info["color"] = override["color"]
                info["operator"] = override["operator"]
                info["category"] = override["category"]
                info["wiki"] = override.get("wiki", "")
                info["potus_fleet"] = override.get("fleet", "")
            _plane_alert_db[icao_hex] = info
        logger.info("plane_alert_db loaded", count=len(_plane_alert_db))
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.error("failed to load plane_alert_db", error=str(exc))

    return _plane_alert_db


def _get_tracked_names_db() -> dict[str, dict]:
    """Lazy-load tracked_names.json into memory on first access."""
    global _tracked_names_db
    if _tracked_names_db is not None:
        return _tracked_names_db

    _tracked_names_db = {}
    if not _TRACKED_NAMES_PATH.exists():
        logger.warning("tracked_names.json not found", path=str(_TRACKED_NAMES_PATH))
        return _tracked_names_db

    try:
        data: dict = json.loads(_TRACKED_NAMES_PATH.read_text(encoding="utf-8"))
        for name, info in data.get("details", {}).items():
            cat = info.get("category", "Other")
            for reg in info.get("registrations", []):
                reg_clean = reg.strip().upper()
                if reg_clean:
                    _tracked_names_db[reg_clean] = {"name": name, "category": cat}
        logger.info("tracked_names_db loaded", count=len(_tracked_names_db))
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.error("failed to load tracked_names_db", error=str(exc))

    return _tracked_names_db


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_with_plane_alert(flight: dict) -> dict:
    """If flight's icao24 is in the Plane-Alert DB, add alert metadata."""
    db = _get_plane_alert_db()
    icao = flight.get("icao24", "").strip().upper()
    if icao and icao in db:
        info = db[icao]
        flight["alert_category"] = info["category"]
        flight["alert_color"] = info["color"]
        flight["alert_operator"] = info["operator"]
        flight["alert_type"] = info["ac_type"]
        flight["alert_tags"] = info["tags"]
        flight["alert_link"] = info["link"]
        if info.get("wiki"):
            flight["alert_wiki"] = info["wiki"]
        if info.get("potus_fleet"):
            flight["potus_fleet"] = info["potus_fleet"]
        if info["registration"]:
            flight["registration"] = info["registration"]
    return flight


def enrich_with_tracked_names(flight: dict) -> dict:
    """If flight's registration matches tracked names, tag it accordingly."""
    icao = flight.get("icao24", "").strip().upper()
    if icao in _POTUS_FLEET:
        return flight

    db = _get_tracked_names_db()
    reg = flight.get("registration", "").strip().upper()
    callsign = flight.get("callsign", "").strip().upper()

    match = None
    if reg and reg in db:
        match = db[reg]
    elif callsign and callsign in db:
        match = db[callsign]

    if match:
        name = match["name"]
        flight["alert_operator"] = name
        flight["alert_category"] = match["category"]

        name_lower = name.lower()
        is_gov = any(
            w in name_lower
            for w in [
                "state of ",
                "government",
                "republic",
                "ministry",
                "department",
                "federal",
                "cia",
            ]
        )
        is_law = any(
            w in name_lower
            for w in [
                "police",
                "marshal",
                "sheriff",
                "douane",
                "customs",
                "patrol",
                "gendarmerie",
                "guardia",
                "law enforcement",
            ]
        )
        is_med = any(
            w in name_lower
            for w in [
                "fire",
                "bomberos",
                "ambulance",
                "paramedic",
                "medevac",
                "rescue",
                "hospital",
                "medical",
                "lifeflight",
            ]
        )

        if is_gov or is_law:
            flight["alert_color"] = "blue"
        elif is_med:
            flight["alert_color"] = "#32cd32"
        elif "alert_color" not in flight:
            flight["alert_color"] = "pink"

    return flight
