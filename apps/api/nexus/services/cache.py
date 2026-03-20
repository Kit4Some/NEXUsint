"""Redis-based caching service for Neo4j queries and analytics results."""

import hashlib
import json
from typing import Any

import structlog
import redis.asyncio as aioredis

logger = structlog.get_logger()


class CacheService:
    """Generic typed cache backed by Redis with key namespacing."""

    _PREFIX = "nexus"

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    def _key(self, domain: str, key: str) -> str:
        return f"{self._PREFIX}:{domain}:{key}"

    async def get(self, domain: str, key: str) -> Any | None:
        """Get a cached value. Returns None on miss."""
        raw = await self._redis.get(self._key(domain, key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, domain: str, key: str, value: Any, ttl: int = 300) -> None:
        """Set a cache value with TTL in seconds."""
        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError):
            logger.warning("cache.serialize_failed", domain=domain, key=key)
            return
        await self._redis.setex(self._key(domain, key), ttl, serialized)

    async def delete(self, domain: str, key: str) -> None:
        """Delete a cached value."""
        await self._redis.delete(self._key(domain, key))

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern. Returns count deleted."""
        full_pattern = f"{self._PREFIX}:{pattern}"
        count = 0
        async for key in self._redis.scan_iter(match=full_pattern):
            await self._redis.delete(key)
            count += 1
        return count

    # --- Domain-specific convenience methods ---

    async def cache_entity(self, entity_id: str, data: dict, ttl: int = 300) -> None:
        await self.set("entity", entity_id, data, ttl)

    async def get_entity(self, entity_id: str) -> dict | None:
        return await self.get("entity", entity_id)

    async def invalidate_entity(self, entity_id: str) -> None:
        await self.delete("entity", entity_id)

    async def cache_search(self, query_hash: str, results: list, ttl: int = 60) -> None:
        await self.set("search", query_hash, results, ttl)

    async def get_search(self, query_hash: str) -> list | None:
        return await self.get("search", query_hash)

    async def cache_analytics(self, algo: str, results: Any, ttl: int = 120) -> None:
        await self.set("analytics", algo, results, ttl)

    async def get_analytics(self, algo: str) -> Any | None:
        return await self.get("analytics", algo)

    async def invalidate_analytics(self) -> int:
        return await self.invalidate_pattern("analytics:*")

    @staticmethod
    def hash_query(query: str, params: dict | None = None) -> str:
        """Create a deterministic hash for a query + params combination."""
        raw = query + json.dumps(params or {}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
