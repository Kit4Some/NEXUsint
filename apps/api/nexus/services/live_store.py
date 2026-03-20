"""Redis-backed live data store for real-time OSINT feeds.

Replaces Shadowbroker's in-memory ``latest_data`` dict with a Redis store
so data survives across worker restarts and can be shared by multiple
Celery workers + the API process.

Key pattern: ``nexus:live:{data_key}``
Freshness:   ``nexus:live:timestamps`` (Redis hash)
Active flag: ``nexus:live:active``
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import structlog
import redis.asyncio as aioredis

from nexus.config import settings

logger = structlog.get_logger()

_REDIS_PREFIX = "nexus:live"
_TIMESTAMPS_KEY = f"{_REDIS_PREFIX}:timestamps"
_ACTIVE_KEY = f"{_REDIS_PREFIX}:active"

# Default TTLs per data category (seconds)
_DEFAULT_TTL = 300  # 5 minutes
_FAST_TTL = 120     # 2 minutes for fast-tier (flights, ships)


async def _get_redis() -> aioredis.Redis:
    """Return a short-lived Redis connection."""
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def set_live_data(
    key: str,
    data: Any,
    ttl: int | None = None,
) -> None:
    """Store *data* under ``nexus:live:{key}`` with an optional TTL."""
    r = await _get_redis()
    try:
        full_key = f"{_REDIS_PREFIX}:{key}"
        payload = json.dumps(data, default=str, ensure_ascii=False)
        effective_ttl = ttl or _DEFAULT_TTL
        await r.set(full_key, payload, ex=effective_ttl)
        # Record freshness
        now = datetime.now(timezone.utc).isoformat()
        await r.hset(_TIMESTAMPS_KEY, key, now)
        logger.debug("live_store.set", key=key, size=len(payload))
    finally:
        await r.aclose()


async def get_live_data(key: str) -> Any | None:
    """Retrieve a single live data key.  Returns *None* if missing/expired."""
    r = await _get_redis()
    try:
        raw = await r.get(f"{_REDIS_PREFIX}:{key}")
        if raw is None:
            return None
        return json.loads(raw)
    finally:
        await r.aclose()


async def get_all_live_data(*keys: str) -> dict[str, Any]:
    """Retrieve multiple live data keys in one round-trip (pipeline)."""
    r = await _get_redis()
    try:
        pipe = r.pipeline()
        for k in keys:
            pipe.get(f"{_REDIS_PREFIX}:{k}")
        results = await pipe.execute()
        out: dict[str, Any] = {}
        for k, raw in zip(keys, results):
            if raw is not None:
                try:
                    out[k] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    out[k] = raw
        return out
    finally:
        await r.aclose()


async def get_timestamps() -> dict[str, str]:
    """Return per-source freshness timestamps."""
    r = await _get_redis()
    try:
        return await r.hgetall(_TIMESTAMPS_KEY)
    finally:
        await r.aclose()


async def get_source_counts(*keys: str) -> dict[str, int]:
    """Return item counts per key (for health endpoint)."""
    data = await get_all_live_data(*keys)
    counts: dict[str, int] = {}
    for k, v in data.items():
        if isinstance(v, list):
            counts[k] = len(v)
        elif isinstance(v, dict):
            counts[k] = 1
        else:
            counts[k] = 0
    return counts


# ── Active flag ──────────────────────────────────────────────────────────


async def is_live_feed_active() -> bool:
    r = await _get_redis()
    try:
        return (await r.get(_ACTIVE_KEY)) == "1"
    finally:
        await r.aclose()


async def set_live_feed_active(active: bool) -> None:
    r = await _get_redis()
    try:
        if active:
            await r.set(_ACTIVE_KEY, "1")
        else:
            await r.delete(_ACTIVE_KEY)
    finally:
        await r.aclose()


# ── Publish helper ───────────────────────────────────────────────────────


async def publish_live_event(event: str, data: Any) -> None:
    """Publish a live feed event through the existing Redis → WebSocket bridge."""
    r = await _get_redis()
    try:
        payload = json.dumps({"event": event, "data": data}, default=str, ensure_ascii=False)
        await r.publish("nexus:ws:events", payload)
    finally:
        await r.aclose()
