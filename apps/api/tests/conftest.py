"""Test fixtures for NEXUS API."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from nexus.main import app
from nexus.dependencies import lifespan_state


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j async driver."""
    driver = AsyncMock()
    session = AsyncMock()
    result = AsyncMock()
    result.data = AsyncMock(return_value=[])

    session.run = AsyncMock(return_value=result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    driver.session = MagicMock(return_value=session)

    return driver


@pytest.fixture
def mock_pg_pool():
    """Mock PostgreSQL connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=conn)
    return pool


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    return redis


@pytest.fixture
async def client(mock_neo4j_driver, mock_pg_pool, mock_redis):
    """Create test HTTP client with mocked dependencies."""
    lifespan_state.neo4j_driver = mock_neo4j_driver
    lifespan_state.pg_pool = mock_pg_pool
    lifespan_state.redis = mock_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
