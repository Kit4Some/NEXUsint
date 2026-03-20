"""GDS (Graph Data Science) projection lifecycle manager."""

import time
from typing import Any

import structlog

from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.services.cache import CacheService

logger = structlog.get_logger()

# Default projection definitions
_PROJECTIONS = {
    "nexus-full": {
        "node_query": "MATCH (n:Entity) RETURN id(n) AS id",
        "rel_query": "MATCH (n:Entity)-[r]->(m:Entity) RETURN id(n) AS source, id(m) AS target, type(r) AS type",
    },
    "nexus-community": {
        "node_query": "MATCH (n:Entity) RETURN id(n) AS id",
        "rel_query": "MATCH (n:Entity)-[r]->(m:Entity) RETURN id(n) AS source, id(m) AS target",
    },
}

_PROJECTION_MAX_AGE = 600  # seconds


class GDSProjectionManager:
    """Manages GDS graph projections to avoid recreating them on every algorithm call."""

    def __init__(self, client: Neo4jClient, cache: CacheService) -> None:
        self._client = client
        self._cache = cache

    async def ensure_projection(self, name: str) -> bool:
        """Ensure a named projection exists and is fresh. Returns True if usable."""
        # Check cache for projection metadata
        meta = await self._cache.get("gds_projection", name)
        if meta and (time.time() - meta.get("created_at", 0)) < _PROJECTION_MAX_AGE:
            return True

        # Check if projection exists in GDS
        exists = await self._projection_exists(name)
        if exists:
            await self._cache.set("gds_projection", name, {"created_at": time.time()}, ttl=_PROJECTION_MAX_AGE)
            return True

        # Create the projection
        definition = _PROJECTIONS.get(name)
        if not definition:
            logger.warning("gds.unknown_projection", name=name)
            return False

        return await self._create_projection(name, definition)

    async def _projection_exists(self, name: str) -> bool:
        """Check if a GDS projection exists."""
        try:
            results = await self._client.execute_read(
                "CALL gds.graph.exists($name) YIELD exists",
                {"name": name},
            )
            return bool(results and results[0].get("exists"))
        except Exception:
            return False

    async def _create_projection(self, name: str, definition: dict[str, str]) -> bool:
        """Create a GDS cypher projection."""
        try:
            await self._client.execute_write(
                """
                CALL gds.graph.project.cypher(
                    $name,
                    $node_query,
                    $rel_query
                )
                """,
                {
                    "name": name,
                    "node_query": definition["node_query"],
                    "rel_query": definition["rel_query"],
                },
            )
            await self._cache.set(
                "gds_projection", name,
                {"created_at": time.time()},
                ttl=_PROJECTION_MAX_AGE,
            )
            logger.info("gds.projection_created", name=name)
            return True
        except Exception as e:
            logger.error("gds.projection_failed", name=name, error=str(e))
            return False

    async def drop_projection(self, name: str) -> None:
        """Drop a GDS projection."""
        try:
            await self._client.execute_write(
                "CALL gds.graph.drop($name, false)",
                {"name": name},
            )
            await self._cache.delete("gds_projection", name)
            logger.info("gds.projection_dropped", name=name)
        except Exception:
            pass

    async def refresh_projection(self, name: str) -> bool:
        """Drop and recreate a projection."""
        await self.drop_projection(name)
        definition = _PROJECTIONS.get(name)
        if not definition:
            return False
        return await self._create_projection(name, definition)

    async def invalidate_all(self) -> None:
        """Invalidate all cached projection metadata (e.g. after writes)."""
        await self._cache.invalidate_pattern("gds_projection:*")
