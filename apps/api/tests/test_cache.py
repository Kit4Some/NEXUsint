"""Tests for Redis caching layer and GDS projection manager."""

import pytest
from unittest.mock import AsyncMock, patch

from nexus.services.cache import CacheService
from nexus.services.gds_manager import GDSProjectionManager


class TestCacheService:
    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        r.get = AsyncMock(return_value=None)
        r.setex = AsyncMock()
        r.delete = AsyncMock()
        return r

    @pytest.fixture
    def cache(self, mock_redis):
        return CacheService(mock_redis)

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        result = await cache.get("entity", "test-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache, mock_redis):
        mock_redis.get = AsyncMock(return_value='{"id": "test-123", "name": "Test"}')
        result = await cache.get("entity", "test-123")
        assert result == {"id": "test-123", "name": "Test"}

    @pytest.mark.asyncio
    async def test_cache_set(self, cache, mock_redis):
        await cache.set("entity", "test-123", {"id": "test-123"}, ttl=300)
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args
        assert args[0][0] == "nexus:entity:test-123"
        assert args[0][1] == 300

    @pytest.mark.asyncio
    async def test_cache_delete(self, cache, mock_redis):
        await cache.delete("entity", "test-123")
        mock_redis.delete.assert_called_once_with("nexus:entity:test-123")

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache, mock_redis):
        # Mock scan_iter to yield keys
        async def mock_scan(*args, **kwargs):
            for key in [b"nexus:analytics:community", b"nexus:analytics:anomaly"]:
                yield key

        mock_redis.scan_iter = mock_scan
        count = await cache.invalidate_pattern("analytics:*")
        assert count == 2
        assert mock_redis.delete.call_count == 2

    def test_hash_query(self):
        h1 = CacheService.hash_query("MATCH (n) RETURN n", {"id": "123"})
        h2 = CacheService.hash_query("MATCH (n) RETURN n", {"id": "123"})
        h3 = CacheService.hash_query("MATCH (n) RETURN n", {"id": "456"})
        assert h1 == h2  # same query+params → same hash
        assert h1 != h3  # different params → different hash

    @pytest.mark.asyncio
    async def test_entity_convenience(self, cache, mock_redis):
        await cache.cache_entity("e1", {"name": "Test"}, ttl=300)
        mock_redis.setex.assert_called_once()

        mock_redis.get = AsyncMock(return_value='{"name": "Test"}')
        result = await cache.get_entity("e1")
        assert result == {"name": "Test"}


class TestGDSProjectionManager:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self):
        cache = AsyncMock(spec=CacheService)
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        cache.invalidate_pattern = AsyncMock(return_value=0)
        return cache

    @pytest.fixture
    def manager(self, mock_client, mock_cache):
        return GDSProjectionManager(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_ensure_projection_cached(self, manager, mock_cache):
        """Should reuse projection if metadata is cached and fresh."""
        import time
        mock_cache.get = AsyncMock(return_value={"created_at": time.time()})
        result = await manager.ensure_projection("nexus-full")
        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_projection_exists_in_gds(self, manager, mock_client, mock_cache):
        """Should cache existing GDS projection metadata."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_client.execute_read = AsyncMock(return_value=[{"exists": True}])
        result = await manager.ensure_projection("nexus-full")
        assert result is True
        mock_cache.set.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_projection_creates_new(self, manager, mock_client, mock_cache):
        """Should create projection if it doesn't exist."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_client.execute_read = AsyncMock(return_value=[{"exists": False}])
        mock_client.execute_write = AsyncMock(return_value=[])
        result = await manager.ensure_projection("nexus-full")
        assert result is True
        mock_client.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_unknown_projection(self, manager, mock_client, mock_cache):
        """Should return False for unknown projection names."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_client.execute_read = AsyncMock(return_value=[{"exists": False}])
        result = await manager.ensure_projection("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_drop_projection(self, manager, mock_client, mock_cache):
        await manager.drop_projection("nexus-full")
        mock_client.execute_write.assert_called_once()
        mock_cache.delete.assert_called()

    @pytest.mark.asyncio
    async def test_invalidate_all(self, manager, mock_cache):
        await manager.invalidate_all()
        mock_cache.invalidate_pattern.assert_called_once_with("gds_projection:*")
