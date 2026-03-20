"""Async Neo4j driver wrapper for knowledge graph operations."""

from typing import Any

import structlog
from neo4j import AsyncDriver, AsyncManagedTransaction

logger = structlog.get_logger()


class Neo4jClient:
    """Async wrapper around the Neo4j Python driver."""

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        self._driver = driver
        self._database = database

    async def execute_read(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a read transaction and return results as dicts."""
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a write transaction and return results as dicts."""
        async with self._driver.session(database=self._database) as session:

            async def _work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
                result = await tx.run(query, parameters or {})
                return await result.data()

            return await session.execute_write(_work)

    async def execute_write_batch(
        self, queries: list[tuple[str, dict[str, Any] | None]]
    ) -> None:
        """Execute multiple write queries in a single transaction."""
        async with self._driver.session(database=self._database) as session:

            async def _work(tx: AsyncManagedTransaction) -> None:
                for query, params in queries:
                    await tx.run(query, params or {})

            await session.execute_write(_work)

    async def verify_connectivity(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error("neo4j.connectivity_failed", error=str(e))
            return False
