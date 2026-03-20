"""FastAPI dependency injection and lifecycle management."""

from typing import AsyncGenerator

import asyncpg
import redis.asyncio as aioredis
import structlog
from fastapi import HTTPException
from neo4j import AsyncGraphDatabase, AsyncDriver

from nexus.config import settings

logger = structlog.get_logger()


class LifespanState:
    """Manages database connections across the application lifecycle.

    Connections to Neo4j, PostgreSQL, and Redis are attempted at startup but
    failures are non-fatal — the application will start in degraded mode and
    endpoints that depend on an unavailable service will return 503.
    """

    def __init__(self) -> None:
        self.neo4j_driver: AsyncDriver | None = None
        self.pg_pool: asyncpg.Pool | None = None
        self.redis: aioredis.Redis | None = None

    async def startup(self) -> None:
        # --- Neo4j (primary data store — required) ---
        try:
            self.neo4j_driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            logger.info("nexus.neo4j.connected", uri=settings.neo4j_uri)
        except Exception as exc:
            logger.error("nexus.neo4j.connect_failed", error=str(exc))
            # Neo4j is critical — still allow startup for health checks

        # --- PostgreSQL (optional — pgvector, audit logs) ---
        try:
            self.pg_pool = await asyncpg.create_pool(
                dsn=settings.get_postgres_dsn(),
                min_size=1,
                max_size=10,
                timeout=5,
            )
            logger.info("nexus.postgres.connected")
        except Exception as exc:
            logger.warning(
                "nexus.postgres.connect_failed",
                error=str(exc),
                hint="PostgreSQL is optional. Vector search and audit logs will be unavailable.",
            )

        # --- Redis (optional — caching, pub/sub) ---
        try:
            self.redis = aioredis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=5,
            )
            await self.redis.ping()
            logger.info("nexus.redis.connected")
        except Exception as exc:
            logger.warning(
                "nexus.redis.connect_failed",
                error=str(exc),
                hint="Redis is optional. Caching and real-time events will be unavailable.",
            )
            self.redis = None

    async def shutdown(self) -> None:
        if self.neo4j_driver:
            await self.neo4j_driver.close()
        if self.pg_pool:
            await self.pg_pool.close()
        if self.redis:
            await self.redis.close()


lifespan_state = LifespanState()


async def get_neo4j() -> AsyncDriver:
    """Get Neo4j async driver."""
    if lifespan_state.neo4j_driver is None:
        raise HTTPException(status_code=503, detail="Neo4j driver not initialized")
    return lifespan_state.neo4j_driver


async def get_pg_pool() -> asyncpg.Pool:
    """Get PostgreSQL connection pool."""
    if lifespan_state.pg_pool is None:
        raise HTTPException(status_code=503, detail="PostgreSQL pool not initialized")
    return lifespan_state.pg_pool


async def get_pg_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a PostgreSQL connection from the pool."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        yield conn


async def get_redis() -> aioredis.Redis:
    """Get Redis async client."""
    if lifespan_state.redis is None:
        raise HTTPException(status_code=503, detail="Redis not initialized")
    return lifespan_state.redis


async def get_token_blacklist():
    """Get token blacklist service."""
    from nexus.services.token_blacklist import TokenBlacklist

    r = await get_redis()
    return TokenBlacklist(r)


async def get_cache_service():
    """Get cache service wrapping Redis."""
    from nexus.services.cache import CacheService

    r = await get_redis()
    return CacheService(r)


async def get_gds_manager():
    """Get GDS projection manager."""
    from nexus.services.gds_manager import GDSProjectionManager
    from nexus.knowledge.neo4j_client import Neo4jClient

    driver = await get_neo4j()
    cache = await get_cache_service()
    return GDSProjectionManager(Neo4jClient(driver), cache)


async def get_cached_neo4j():
    """Get a caching Neo4j client."""
    from nexus.knowledge.cached_client import CachedNeo4jClient

    driver = await get_neo4j()
    cache = await get_cache_service()
    return CachedNeo4jClient(driver, cache)


async def get_elasticsearch():
    """Get Elasticsearch service."""
    from nexus.services.elasticsearch import ElasticsearchService

    service = ElasticsearchService(settings.elasticsearch_url)
    await service.ensure_indices()
    return service


async def get_vector_search():
    """Get pgvector semantic search service."""
    from nexus.services.vector_search import VectorSearchService

    pool = await get_pg_pool()
    return VectorSearchService(pool, settings.openai_api_key)
