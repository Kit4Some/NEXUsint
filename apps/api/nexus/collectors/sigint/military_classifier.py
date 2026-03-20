"""Military flight tracking and UAV detection from ADS-B data.

Ported from Shadowbroker military.py to async NEXUS patterns.
Fetches live military transponder data from api.adsb.lol and classifies
aircraft into military flights and UAVs with country/force enrichment.
"""

from __future__ import annotations

import structlog

from nexus.utils.http_client import fetch_json
from nexus.services.plane_alert import enrich_with_plane_alert

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants — UAV classification
# ---------------------------------------------------------------------------

UAV_TYPE_CODES: set[str] = {"Q9", "R4", "TB2", "MALE", "HALE", "HERM", "HRON"}

UAV_CALLSIGN_PREFIXES: tuple[str, ...] = (
    "FORTE", "GHAWK", "REAP", "BAMS", "UAV", "UAS",
)

UAV_MODEL_KEYWORDS: tuple[str, ...] = (
    "RQ-", "MQ-", "RQ4", "MQ9", "MQ4", "MQ1",
    "REAPER", "GLOBALHAWK", "TRITON", "PREDATOR",
    "HERMES", "HERON", "BAYRAKTAR",
)

UAV_WIKI: dict[str, str] = {
    "RQ4":        "https://en.wikipedia.org/wiki/Northrop_Grumman_RQ-4_Global_Hawk",
    "RQ-4":       "https://en.wikipedia.org/wiki/Northrop_Grumman_RQ-4_Global_Hawk",
    "MQ4":        "https://en.wikipedia.org/wiki/Northrop_Grumman_MQ-4C_Triton",
    "MQ-4":       "https://en.wikipedia.org/wiki/Northrop_Grumman_MQ-4C_Triton",
    "MQ9":        "https://en.wikipedia.org/wiki/General_Atomics_MQ-9_Reaper",
    "MQ-9":       "https://en.wikipedia.org/wiki/General_Atomics_MQ-9_Reaper",
    "MQ1":        "https://en.wikipedia.org/wiki/General_Atomics_MQ-1C_Gray_Eagle",
    "MQ-1":       "https://en.wikipedia.org/wiki/General_Atomics_MQ-1C_Gray_Eagle",
    "REAPER":     "https://en.wikipedia.org/wiki/General_Atomics_MQ-9_Reaper",
    "GLOBALHAWK": "https://en.wikipedia.org/wiki/Northrop_Grumman_RQ-4_Global_Hawk",
    "TRITON":     "https://en.wikipedia.org/wiki/Northrop_Grumman_MQ-4C_Triton",
    "PREDATOR":   "https://en.wikipedia.org/wiki/General_Atomics_MQ-1_Predator",
    "HERMES":     "https://en.wikipedia.org/wiki/Elbit_Hermes_900",
    "HERON":      "https://en.wikipedia.org/wiki/IAI_Heron",
    "BAYRAKTAR":  "https://en.wikipedia.org/wiki/Bayraktar_TB2",
}

# ---------------------------------------------------------------------------
# Constants — ICAO military country ranges
# ---------------------------------------------------------------------------

ICAO_MILITARY_RANGES: list[tuple[int, int, str, str]] = [
    (0x780000, 0x7BFFFF, "China",        "PLA"),
    (0x840000, 0x87FFFF, "Japan",        "JSDF"),
    (0x700000, 0x71FFFF, "South Korea",  "ROK"),
    (0xE80000, 0xE80FFF, "Taiwan",       "ROC"),
    (0x150000, 0x157FFF, "Russia",       "VKS"),
    (0x7C0000, 0x7FFFFF, "Australia",    "RAAF"),
    (0x758000, 0x75FFFF, "Philippines",  "PAF"),
    (0x768000, 0x76FFFF, "Singapore",    "RSAF"),
    (0x720000, 0x727FFF, "North Korea",  "KPAF"),
]

# ---------------------------------------------------------------------------
# Constants — Military aircraft type classification keywords
# ---------------------------------------------------------------------------

MIL_TYPE_MAP: dict[str, list[str]] = {
    "tanker": ["K35", "K46", "A33", "YY20"],
    "fighter": [
        "F16", "F35", "F22", "F15", "F18", "T38", "T6", "A10",
        "J10", "J11", "J15", "J16", "J20", "JF17",
        "SU27", "SU30", "SU35", "SU57", "MIG29", "MIG31",
        "F15J", "F2", "IDF", "FA50", "KF21",
    ],
    "bomber": ["TU95", "TU160", "TU22"],
    "cargo": [
        "C17", "C5", "C130", "C30", "A400", "V22",
        "Y20", "Y9", "Y8", "C2",
        "IL76", "AN124", "AN12",
    ],
    "recon": [
        "P8", "E3", "E8", "U2",
        "KJ500", "KJ200", "GX11", "P1", "E767", "E2K", "E2C",
        "A50", "TU214R", "IL20",
    ],
}

_ADSB_MIL_URL = "https://api.adsb.lol/v2/mil"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _enrich_country(icao_hex: str, flag: str) -> tuple[str, str]:
    """Infer country and force from ICAO address range when flag is unknown."""
    if flag and flag not in ("Unknown", "Military Asset", ""):
        return flag, ""
    try:
        addr = int(icao_hex, 16)
    except (ValueError, TypeError):
        return flag or "Military Asset", ""
    for start, end, country, force in ICAO_MILITARY_RANGES:
        if start <= addr <= end:
            return country, force
    return flag or "Military Asset", ""


def _classify_military_type(raw_model: str) -> str:
    """Classify a military aircraft into a category based on its model string."""
    model = raw_model.upper().replace("-", "").replace(" ", "")

    # Helicopters: model contains 'H' and at least one digit
    if "H" in model and any(c.isdigit() for c in model):
        return "heli"

    for category, keywords in MIL_TYPE_MAP.items():
        if any(kw in model for kw in keywords):
            return category

    return "default"


def _classify_uav(model: str, callsign: str) -> tuple[bool, str | None, str | None]:
    """Check if an aircraft is a UAV.

    Returns ``(is_uav, uav_type, wiki_url)`` or ``(False, None, None)``.
    """
    model_up = model.upper().replace(" ", "")
    callsign_up = callsign.upper().strip()

    # 1. Match by type code
    if model_up in UAV_TYPE_CODES:
        uav_type = "HALE Surveillance" if model_up in ("R4", "HALE") else "MALE ISR"
        wiki = UAV_WIKI.get(model_up, "")
        return True, uav_type, wiki

    # 2. Match by callsign prefix
    for prefix in UAV_CALLSIGN_PREFIXES:
        if callsign_up.startswith(prefix):
            uav_type = "HALE Surveillance" if prefix in ("FORTE", "GHAWK", "BAMS") else "MALE ISR"
            wiki = UAV_WIKI.get(prefix, "")
            if prefix == "FORTE":
                wiki = UAV_WIKI["RQ4"]
            elif prefix == "BAMS":
                wiki = UAV_WIKI["MQ4"]
            return True, uav_type, wiki

    # 3. Match by model keyword
    for kw in UAV_MODEL_KEYWORDS:
        if kw in model_up:
            if any(h in model_up for h in ("RQ4", "RQ-4", "GLOBALHAWK")):
                return True, "HALE Surveillance", UAV_WIKI.get(kw, "")
            elif any(h in model_up for h in ("MQ4", "MQ-4", "TRITON")):
                return True, "HALE Maritime Surveillance", UAV_WIKI.get(kw, "")
            elif any(h in model_up for h in ("MQ9", "MQ-9", "REAPER")):
                return True, "MALE Strike/ISR", UAV_WIKI.get(kw, "")
            elif any(h in model_up for h in ("MQ1", "MQ-1", "PREDATOR")):
                return True, "MALE ISR/Strike", UAV_WIKI.get(kw, "")
            elif "BAYRAKTAR" in model_up or "TB2" in model_up:
                return True, "MALE Strike", UAV_WIKI.get("BAYRAKTAR", "")
            elif "HERMES" in model_up:
                return True, "MALE ISR", UAV_WIKI.get("HERMES", "")
            elif "HERON" in model_up:
                return True, "MALE ISR", UAV_WIKI.get("HERON", "")
            return True, "MALE ISR", UAV_WIKI.get(kw, "")

    return False, None, None


def _parse_aircraft(f: dict) -> dict | None:
    """Parse a single ADS-B record into a normalized aircraft dict.

    Returns ``None`` if the record should be skipped (missing coords, TWR, etc.).
    """
    lat = f.get("lat")
    lng = f.get("lon")
    if lat is None or lng is None:
        return None

    model = str(f.get("t", "UNKNOWN")).upper()
    callsign = str(f.get("flight", "MIL-UNKN")).strip()

    # Skip ground towers
    if model == "TWR":
        return None

    alt_raw = f.get("alt_baro")
    alt_value = alt_raw * 0.3048 if isinstance(alt_raw, (int, float)) else 0

    gs_knots = f.get("gs")
    speed_knots = round(gs_knots, 1) if isinstance(gs_knots, (int, float)) else None

    icao_hex = f.get("hex", "")
    heading = f.get("track") or 0

    is_uav, uav_type, wiki_url = _classify_uav(model, callsign)

    if is_uav:
        uav_country, uav_force = _enrich_country(icao_hex, f.get("flag", ""))
        return {
            "id": f"uav-{icao_hex}",
            "callsign": callsign,
            "aircraft_model": f.get("t", "Unknown"),
            "lat": float(lat),
            "lng": float(lng),
            "alt": alt_value,
            "heading": heading,
            "speed_knots": speed_knots,
            "country": uav_country,
            "force": uav_force,
            "uav_type": uav_type,
            "wiki": wiki_url or "",
            "type": "uav",
            "registration": f.get("r", "N/A"),
            "icao24": icao_hex,
            "squawk": f.get("squawk", ""),
        }

    mil_country, mil_force = _enrich_country(icao_hex, f.get("flag", ""))
    mil_cat = _classify_military_type(f.get("t", "UNKNOWN"))

    return {
        "callsign": callsign,
        "country": mil_country,
        "force": mil_force,
        "lng": float(lng),
        "lat": float(lat),
        "alt": alt_value,
        "heading": heading,
        "type": "military_flight",
        "military_type": mil_cat,
        "origin_loc": None,
        "dest_loc": None,
        "origin_name": "UNKNOWN",
        "dest_name": "UNKNOWN",
        "registration": f.get("r", "N/A"),
        "model": f.get("t", "Unknown"),
        "icao24": icao_hex,
        "speed_knots": speed_knots,
        "squawk": f.get("squawk", ""),
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def fetch_military_flights() -> dict:
    """Fetch and classify military flights from ADS-B Exchange.

    Returns a dict with two keys:

    * ``military_flights`` -- list of non-UAV military aircraft dicts
    * ``uavs`` -- list of detected UAV dicts

    Each military flight is also cross-referenced against the Plane-Alert
    database; flights that match an alert entry are promoted to
    ``tracked_flight`` type and included separately under the
    ``tracked_flights`` key.
    """
    military_flights: list[dict] = []
    detected_uavs: list[dict] = []

    try:
        data = await fetch_json(_ADSB_MIL_URL, timeout=10)
        ac_list: list[dict] = data.get("ac", []) if isinstance(data, dict) else []
    except Exception:
        log.error("military_fetch_failed", url=_ADSB_MIL_URL)
        return {"military_flights": [], "uavs": [], "tracked_flights": []}

    for f in ac_list:
        try:
            parsed = _parse_aircraft(f)
            if parsed is None:
                continue
            if parsed["type"] == "uav":
                detected_uavs.append(parsed)
            else:
                military_flights.append(parsed)
        except Exception:
            log.error("military_aircraft_parse_error", icao=f.get("hex", "?"))
            continue

    log.info(
        "military_flights_fetched",
        military_count=len(military_flights),
        uav_count=len(detected_uavs),
    )

    # Cross-reference with Plane-Alert DB
    tracked_flights: list[dict] = []
    remaining_mil: list[dict] = []

    for mf in military_flights:
        enriched = enrich_with_plane_alert(mf)
        if enriched.get("alert_category"):
            enriched["type"] = "tracked_flight"
            tracked_flights.append(enriched)
        else:
            remaining_mil.append(enriched)

    if tracked_flights:
        log.info(
            "military_tracked_flights",
            tracked_count=len(tracked_flights),
        )

    return {
        "military_flights": remaining_mil,
        "uavs": detected_uavs,
        "tracked_flights": tracked_flights,
    }
