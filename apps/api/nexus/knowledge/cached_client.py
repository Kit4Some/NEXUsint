"""Caching wrapper around Neo4jClient for read query acceleration."""

from typing import Any

import structlog

from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.services.cache import CacheService

logger = structlog.get_logger()

# Default TTL by query pattern prefix (seconds)
_DEFAULT_READ_TTL = 120
_PATTERN_TTLS = {
    "MATCH (e:Entity {id:": 300,     # single entity lookups
    "CALL db.index.fulltext": 60,     # full-text search
    "CALL gds.": 120,                 # GDS algorithm results
    "MATCH path =": 120,              # subgraph queries
}


class CachedNeo4jClient(Neo4jClient):
    """Neo4jClient wrapper that caches read query results in Redis."""

    def __init__(self, driver: Any, cache: CacheService, database: str = "neo4j") -> None:
        super().__init__(driver, database)
        self._cache = cache

    async def execute_read(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a read transaction with caching."""
        cache_key = CacheService.hash_query(query, parameters)

        # Try cache first
        cached = await self._cache.get("neo4j_read", cache_key)
        if cached is not None:
            return cached

        # Execute query
        results = await super().execute_read(query, parameters)

        # Cache the results
        ttl = self._get_ttl(query)
        await self._cache.set("neo4j_read", cache_key, results, ttl)

        return results

    async def execute_write(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a write transaction and invalidate related caches."""
        results = await super().execute_write(query, parameters)

        # Invalidate read caches after writes
        await self._cache.invalidate_pattern("neo4j_read:*")
        await self._cache.invalidate_pattern("analytics:*")

        return results

    async def execute_write_batch(
        self, queries: list[tuple[str, dict[str, Any] | None]]
    ) -> None:
        """Execute batch writes and invalidate caches."""
        await super().execute_write_batch(queries)
        await self._cache.invalidate_pattern("neo4j_read:*")
        await self._cache.invalidate_pattern("analytics:*")

    def _get_ttl(self, query: str) -> int:
        """Determine cache TTL based on query pattern."""
        normalized = query.strip()
        for pattern, ttl in _PATTERN_TTLS.items():
            if normalized.startswith(pattern):
                return ttl
        return _DEFAULT_READ_TTL
