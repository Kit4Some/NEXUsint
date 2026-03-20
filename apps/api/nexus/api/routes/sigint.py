"""SIGINT routes — live flight/vessel tracking and track retrieval."""

from fastapi import APIRouter, Query

from nexus.collectors.sigint.adsb_collector import ADSBCollector
from nexus.collectors.sigint.ais_collector import AISCollector
from nexus.collectors.base import CollectionQuery

router = APIRouter()


@router.get("/flights")
async def get_live_flights(
    south: float = Query(..., description="South latitude"),
    west: float = Query(..., description="West longitude"),
    north: float = Query(..., description="North latitude"),
    east: float = Query(..., description="East longitude"),
):
    """Get live aircraft positions within a bounding box."""
    collector = ADSBCollector()
    try:
        results = await collector.collect(CollectionQuery(
            query="",
            scan_type="area_aircraft",
            options={"lamin": south, "lomin": west, "lamax": north, "lomax": east},
        ))
        return {
            "flights": [r.normalized for r in results],
            "count": len(results),
        }
    finally:
        await collector.close()


@router.get("/flights/{icao24}/track")
async def get_flight_track(icao24: str):
    """Get historical flight track for an aircraft by ICAO24 address."""
    collector = ADSBCollector()
    try:
        results = await collector.collect(CollectionQuery(
            query=icao24, scan_type="aircraft_track",
        ))
        return {
            "icao24": icao24,
            "track": [r.normalized for r in results],
            "point_count": len(results),
        }
    finally:
        await collector.close()


@router.get("/flights/{icao24}")
async def get_aircraft_state(icao24: str):
    """Get current state of a specific aircraft."""
    collector = ADSBCollector()
    try:
        results = await collector.collect(CollectionQuery(
            query=icao24, scan_type="aircraft_state",
        ))
        if not results:
            return {"icao24": icao24, "state": None}
        return {"icao24": icao24, "state": results[0].normalized}
    finally:
        await collector.close()


@router.get("/vessels")
async def get_live_vessels(
    south: float = Query(..., description="South latitude"),
    west: float = Query(..., description="West longitude"),
    north: float = Query(..., description="North latitude"),
    east: float = Query(..., description="East longitude"),
):
    """Get live vessel positions within a bounding box."""
    collector = AISCollector()
    try:
        results = await collector.collect(CollectionQuery(
            query="",
            scan_type="area_vessels",
            options={"south": south, "west": west, "north": north, "east": east},
        ))
        return {
            "vessels": [r.normalized for r in results],
            "count": len(results),
        }
    finally:
        await collector.close()


@router.get("/vessels/{mmsi}/track")
async def get_vessel_track(mmsi: str):
    """Get historical vessel track by MMSI."""
    collector = AISCollector()
    try:
        results = await collector.collect(CollectionQuery(
            query=mmsi, scan_type="vessel_track",
        ))
        return {
            "mmsi": mmsi,
            "track": [r.normalized for r in results],
            "point_count": len(results),
        }
    finally:
        await collector.close()


@router.get("/vessels/{mmsi}")
async def get_vessel_info(mmsi: str):
    """Get vessel information by MMSI."""
    collector = AISCollector()
    try:
        results = await collector.collect(CollectionQuery(
            query=mmsi, scan_type="vessel_info",
        ))
        if not results:
            return {"mmsi": mmsi, "vessel": None}
        return {"mmsi": mmsi, "vessel": results[0].normalized}
    finally:
        await collector.close()
