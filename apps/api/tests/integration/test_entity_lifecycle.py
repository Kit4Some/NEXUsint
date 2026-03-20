"""Integration test: entity lifecycle — create, search, graph, merge."""

import pytest
from unittest.mock import AsyncMock

from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.repository import EntityRepository
from nexus.services.cache import CacheService


class TestEntityLifecycle:
    """End-to-end entity lifecycle test with cache integration."""

    @pytest.fixture
    def mock_neo4j(self):
        client = AsyncMock(spec=Neo4jClient)
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = AsyncMock(spec=CacheService)
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        cache.invalidate_pattern = AsyncMock(return_value=0)
        cache.invalidate_entity = AsyncMock()
        cache.invalidate_analytics = AsyncMock(return_value=0)
        return cache

    @pytest.fixture
    def repo(self, mock_neo4j, mock_cache):
        return EntityRepository(mock_neo4j, mock_cache)

    @pytest.mark.asyncio
    async def test_create_entity_invalidates_cache(self, repo, mock_neo4j, mock_cache):
        """Creating an entity should invalidate search and analytics caches."""
        from nexus.models.entity import EntityCreate, EntityType

        mock_neo4j.execute_write = AsyncMock(return_value=[{"e": {}}])

        entity = EntityCreate(
            name="Test Actor",
            type=EntityType.ThreatActor,
            confidence=0.8,
            source_int="CYBINT",
            risk_score=5.0,
        )

        result = await repo.create_entity(entity)
        assert result.name == "Test Actor"

        # Verify cache invalidation was called
        mock_cache.invalidate_pattern.assert_called_with("search:*")
        mock_cache.invalidate_analytics.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_entity(self, repo, mock_neo4j):
        """Get entity should return formatted response."""
        mock_neo4j.execute_read = AsyncMock(return_value=[{
            "id": "threatactor-abc",
            "name": "APT-28",
            "type": "ThreatActor",
            "properties": "{}",
            "confidence": 0.9,
            "source_int": "CYBINT",
            "risk_score": 8.5,
            "first_seen": "2024-01-01",
            "last_seen": "2024-06-01",
            "created_at": "2024-01-01",
            "updated_at": "2024-06-01",
        }])

        result = await repo.get_entity("threatactor-abc")
        assert result is not None
        assert result.name == "APT-28"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_merge_invalidates_both_entities(self, repo, mock_neo4j, mock_cache):
        """Merging entities should invalidate both entity caches."""
        mock_neo4j.execute_write = AsyncMock(return_value=[{"id": "target"}])
        mock_neo4j.execute_read = AsyncMock(return_value=[{
            "id": "target",
            "name": "Target",
            "type": "ThreatActor",
            "properties": "{}",
            "confidence": 0.9,
            "source_int": "CYBINT",
            "risk_score": 7.0,
            "first_seen": "2024-01-01",
            "last_seen": "2024-06-01",
            "created_at": "2024-01-01",
            "updated_at": "2024-06-01",
        }])

        await repo.merge_entities("source", "target")

        # Both entity caches should be invalidated
        assert mock_cache.invalidate_entity.call_count == 2
        mock_cache.invalidate_entity.assert_any_call("source")
        mock_cache.invalidate_entity.assert_any_call("target")
        mock_cache.invalidate_analytics.assert_called()
