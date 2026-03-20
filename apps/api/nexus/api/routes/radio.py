"""REST endpoints for radio intercept features."""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/top")
async def get_top_feeds():
    """Return Broadcastify top 50 scanner feeds."""
    from nexus.collectors.osint_feeds.radio_intercept import fetch_radio_top

    return await fetch_radio_top()


@router.get("/systems")
async def get_openmhz_systems():
    """Return all OpenMHz trunked radio systems."""
    from nexus.collectors.osint_feeds.radio_intercept import fetch_openmhz_systems

    return await fetch_openmhz_systems()


@router.get("/nearest")
async def get_nearest_radio(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    limit: int = Query(5, ge=1, le=20),
):
    """Find nearest OpenMHz radio systems by coordinates."""
    from nexus.collectors.osint_feeds.radio_intercept import fetch_nearest_radio

    return await fetch_nearest_radio(lat, lng, limit)
