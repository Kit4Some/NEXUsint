"""REST endpoints for the real-time live feed system."""

from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, BackgroundTasks, Request, Response

from nexus.services.live_store import (
    get_all_live_data,
    get_timestamps,
    get_source_counts,
    is_live_feed_active,
    set_live_feed_active,
)

router = APIRouter()

_FAST_KEYS = (
    "commercial_flights",
    "private_jets",
    "private_flights",
    "tracked_flights",
    "military_flights",
    "uavs",
    "gps_jamming",
    "satellites",
)

_SLOW_KEYS = (
    "news",
    "earthquakes",
    "fires",
    "weather",
    "space_weather",
    "stocks",
    "oil",
    "gdelt",
    "frontlines",
    "internet_outages",
    "kiwisdr",
    "airports",
    "military_bases",
    "datacenters",
    "power_plants",
)

_ALL_KEYS = _FAST_KEYS + _SLOW_KEYS


def _etag_response(data: dict, request: Request) -> Response:
    """Build a JSON response with ETag support for 304 caching."""
    body = json.dumps(data, default=str)
    etag = hashlib.md5(body.encode()).hexdigest()  # noqa: S324

    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304)

    return Response(
        content=body,
        media_type="application/json",
        headers={"ETag": f'"{etag}"'},
    )


@router.get("/fast")
async def get_fast_data(request: Request) -> Response:
    """Return fast-tier live data (flights, military, satellites)."""
    data = await get_all_live_data(*_FAST_KEYS)

    # On-demand collection if Redis is empty and live feed is active
    if not data and await is_live_feed_active():
        try:
            from nexus.tasks.live_feed_tasks import _fast_collect
            await _fast_collect()
            data = await get_all_live_data(*_FAST_KEYS)
        except Exception:
            pass

    timestamps = await get_timestamps()
    data["freshness"] = timestamps
    return _etag_response(data, request)


@router.get("/slow")
async def get_slow_data(request: Request) -> Response:
    """Return slow-tier live data (news, earthquakes, fires, etc.)."""
    data = await get_all_live_data(*_SLOW_KEYS)

    # On-demand collection if Redis is empty and live feed is active
    if not data and await is_live_feed_active():
        try:
            from nexus.tasks.live_feed_tasks import _slow_collect
            await _slow_collect()
            data = await get_all_live_data(*_SLOW_KEYS)
        except Exception:
            pass

    timestamps = await get_timestamps()
    data["freshness"] = timestamps
    return _etag_response(data, request)


@router.get("/health")
async def get_health():
    """Return source counts and freshness timestamps."""
    counts = await get_source_counts(*_ALL_KEYS)
    timestamps = await get_timestamps()
    active = await is_live_feed_active()
    return {
        "active": active,
        "sources": counts,
        "freshness": timestamps,
    }


@router.post("/start")
async def start_live_feed(background_tasks: BackgroundTasks):
    """Activate the live feed and trigger immediate first collection."""
    await set_live_feed_active(True)

    # Run first collection immediately in the background (no Celery needed)
    async def _initial_collect():
        try:
            from nexus.tasks.live_feed_tasks import _fast_collect, _slow_collect
            await _fast_collect()
            await _slow_collect()
        except Exception:
            pass

    background_tasks.add_task(_initial_collect)

    return {"status": "started"}


@router.post("/stop")
async def stop_live_feed():
    """Deactivate the live feed — Celery Beat tasks will skip collection."""
    await set_live_feed_active(False)
    return {"status": "stopped"}
