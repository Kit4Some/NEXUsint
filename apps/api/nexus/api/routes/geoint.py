"""GEOINT routes — satellite imagery, OSM features, geocoding."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from nexus.collectors.base import CollectionQuery
from nexus.collectors.geoint.geocoder_service import GeocoderService
from nexus.collectors.geoint.overpass_collector import OverpassCollector
from nexus.collectors.geoint.sentinel_collector import SentinelCollector

router = APIRouter()

# Collector singletons (lazy-init in production; here for simplicity)
_sentinel = SentinelCollector()
_overpass = OverpassCollector()
_geocoder = GeocoderService()


@router.get("/satellite/search")
async def search_satellite_imagery(
    south: float = Query(..., ge=-90, le=90),
    west: float = Query(..., ge=-180, le=180),
    north: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    date_start: str = Query("", description="ISO date YYYY-MM-DD"),
    date_end: str = Query("", description="ISO date YYYY-MM-DD"),
    max_cloud_cover: float = Query(20.0, ge=0, le=100),
) -> dict[str, Any]:
    """Search Sentinel-2 imagery for a bounding box and date range."""
    cq = CollectionQuery(
        query="satellite_search",
        scan_type="satellite_search",
        options={
            "bbox": {"south": south, "west": west, "north": north, "east": east},
            "date_start": date_start,
            "date_end": date_end,
            "max_cloud_cover": max_cloud_cover,
        },
    )
    results = await _sentinel.collect(cq)
    return {
        "count": len(results),
        "products": [r.normalized for r in results],
    }


@router.get("/satellite/{product_id}")
async def get_satellite_metadata(product_id: str) -> dict[str, Any]:
    """Get metadata for a specific Sentinel-2 product."""
    cq = CollectionQuery(query=product_id, scan_type="satellite_metadata")
    results = await _sentinel.collect(cq)
    if not results:
        raise HTTPException(status_code=404, detail="Product not found")
    return results[0].normalized


@router.get("/osm/features")
async def get_osm_features(
    south: float = Query(..., ge=-90, le=90),
    west: float = Query(..., ge=-180, le=180),
    north: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    amenity: str = Query(None),
    landuse: str = Query(None),
    building: str = Query(None),
    natural: str = Query(None),
    tourism: str = Query(None),
) -> dict[str, Any]:
    """Get OSM features within a bounding box with optional tag filters."""
    tags: dict[str, str] = {}
    if amenity:
        tags["amenity"] = amenity
    if landuse:
        tags["landuse"] = landuse
    if building:
        tags["building"] = building
    if natural:
        tags["natural"] = natural
    if tourism:
        tags["tourism"] = tourism

    cq = CollectionQuery(
        query="osm_features",
        scan_type="osm_bbox",
        options={
            "bbox": {"south": south, "west": west, "north": north, "east": east},
            "tags": tags,
        },
    )
    results = await _overpass.collect(cq)
    return {
        "count": len(results),
        "features": [r.normalized for r in results],
    }


@router.get("/geocode/forward")
async def geocode_forward(
    q: str = Query(..., min_length=2, description="Placename to geocode"),
) -> dict[str, Any]:
    """Forward geocode a placename to WGS84 coordinates."""
    results = await _geocoder.forward_geocode(q)
    return {
        "query": q,
        "count": len(results),
        "results": [r.normalized for r in results],
    }


@router.get("/geocode/reverse")
async def geocode_reverse(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict[str, Any]:
    """Reverse geocode coordinates to a placename."""
    results = await _geocoder.reverse_geocode(lat, lon)
    if not results:
        raise HTTPException(status_code=404, detail="No results for coordinates")
    return results[0].normalized


@router.post("/geocode/batch")
async def geocode_batch(placenames: list[str]) -> dict[str, Any]:
    """Batch forward geocode multiple placenames."""
    if len(placenames) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 placenames per batch")
    results = await _geocoder.batch_geocode(placenames)
    return {
        "count": len(results),
        "results": [r.normalized for r in results],
    }
