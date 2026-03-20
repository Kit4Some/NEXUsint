"""Earth-observation fetchers -- earthquakes, FIRMS fires, space weather, weather radar.

Ported from Shadowbroker earth_observation.py to async NEXUS patterns.
"""

from __future__ import annotations

import csv
import heapq
import io

import structlog

from nexus.utils.http_client import fetch_json, fetch_text

logger = structlog.get_logger("nexus.collectors.osint_feeds.earth_observation")


# ---------------------------------------------------------------------------
# Earthquakes (USGS)
# ---------------------------------------------------------------------------
async def fetch_earthquakes() -> list[dict]:
    """Fetch M2.5+ earthquakes from the last 24 hours (USGS), top 50."""
    quakes: list[dict] = []
    try:
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        data = await fetch_json(url, timeout=10)
        features = data.get("features", [])
        for f in features[:50]:
            lng, lat, _depth = f["geometry"]["coordinates"]
            quakes.append(
                {
                    "id": f["id"],
                    "mag": f["properties"]["mag"],
                    "lat": lat,
                    "lng": lng,
                    "place": f["properties"]["place"],
                }
            )
        logger.info("earthquakes fetched", count=len(quakes))
    except Exception as exc:
        logger.error("error fetching earthquakes", error=str(exc))
    return quakes


# ---------------------------------------------------------------------------
# NASA FIRMS Fires
# ---------------------------------------------------------------------------
async def fetch_firms_fires() -> list[dict]:
    """Fetch global fire/thermal anomalies from NASA FIRMS (NOAA-20 VIIRS, 24h).

    Returns up to 5000 hotspots sorted by descending fire radiative power (FRP).
    """
    fires: list[dict] = []
    try:
        url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
        text = await fetch_text(url, timeout=30)
        reader = csv.DictReader(io.StringIO(text))
        all_rows: list[dict] = []
        for row in reader:
            try:
                lat = float(row.get("latitude", 0))
                lng = float(row.get("longitude", 0))
                frp = float(row.get("frp", 0))
                all_rows.append(
                    {
                        "lat": lat,
                        "lng": lng,
                        "frp": frp,
                        "brightness": float(row.get("bright_ti4", 0)),
                        "confidence": row.get("confidence", "nominal"),
                        "daynight": row.get("daynight", ""),
                        "acq_date": row.get("acq_date", ""),
                        "acq_time": row.get("acq_time", ""),
                    }
                )
            except (ValueError, TypeError):
                continue
        fires = heapq.nlargest(5000, all_rows, key=lambda x: x["frp"])
        logger.info("firms fires fetched", count=len(fires))
    except Exception as exc:
        logger.error("error fetching firms fires", error=str(exc))
    return fires


# ---------------------------------------------------------------------------
# Space Weather (NOAA SWPC)
# ---------------------------------------------------------------------------
async def fetch_space_weather() -> dict:
    """Fetch NOAA SWPC planetary Kp index and recent solar events."""
    result: dict = {"kp_index": None, "kp_text": "QUIET", "events": []}
    try:
        kp_data = await fetch_json(
            "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json",
            timeout=10,
        )
        if kp_data:
            latest_kp = kp_data[-1]
            kp_value = float(latest_kp.get("kp_index", 0))
            result["kp_index"] = kp_value
            if kp_value >= 5:
                result["kp_text"] = f"STORM G{min(int(kp_value) - 4, 5)}"
            elif kp_value >= 4:
                result["kp_text"] = "ACTIVE"
            elif kp_value >= 3:
                result["kp_text"] = "UNSETTLED"

        all_events = await fetch_json(
            "https://services.swpc.noaa.gov/json/edited_events.json",
            timeout=10,
        )
        events: list[dict] = []
        for ev in all_events[-10:]:
            events.append(
                {
                    "type": ev.get("type", ""),
                    "begin": ev.get("begin", ""),
                    "end": ev.get("end", ""),
                    "classtype": ev.get("classtype", ""),
                }
            )
        result["events"] = events
        logger.info(
            "space weather fetched",
            kp_index=result["kp_index"],
            kp_text=result["kp_text"],
            event_count=len(events),
        )
    except Exception as exc:
        logger.error("error fetching space weather", error=str(exc))
    return result


# ---------------------------------------------------------------------------
# Weather Radar (RainViewer)
# ---------------------------------------------------------------------------
async def fetch_weather() -> dict:
    """Fetch latest radar mosaic timestamps from RainViewer."""
    result: dict = {}
    try:
        data = await fetch_json("https://api.rainviewer.com/public/weather-maps.json", timeout=10)
        if "radar" in data and "past" in data["radar"]:
            latest_time = data["radar"]["past"][-1]["time"]
            result = {
                "time": latest_time,
                "host": data.get("host", "https://tilecache.rainviewer.com"),
            }
            logger.info("weather radar fetched", time=latest_time)
    except Exception as exc:
        logger.error("error fetching weather", error=str(exc))
    return result
