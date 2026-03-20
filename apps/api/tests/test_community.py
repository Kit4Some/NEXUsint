"""Enhanced community detection and analysis tests."""

import pytest
from unittest.mock import AsyncMock

from nexus.analytics.community_analyzer import CommunityAnalyzer
from nexus.analytics.temporal_analyzer import TemporalAnalyzer


class TestCommunityAnalyzer:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock()

    @pytest.fixture
    def analyzer(self, mock_client):
        return CommunityAnalyzer(mock_client)

    @pytest.mark.asyncio
    async def test_detect_communities_enhanced(self, analyzer, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[
            {"id": "e1", "name": "Actor1", "type": "ThreatActor",
             "source_int": "CYBINT", "confidence": 0.8, "risk_score": 7.5, "communityId": 0},
            {"id": "e2", "name": "IP1", "type": "IPAddress",
             "source_int": "CYBINT", "confidence": 0.9, "risk_score": 6.0, "communityId": 0},
            {"id": "e3", "name": "Seoul", "type": "Location",
             "source_int": "GEOINT", "confidence": 0.7, "risk_score": 2.0, "communityId": 1},
        ])

        result = await analyzer.detect_communities_enhanced()
        assert result["community_count"] == 2
        communities = result["communities"]
        assert len(communities) == 2

        # Community 0 has 2 members
        c0 = next(c for c in communities if c["community_id"] == 0)
        assert c0["member_count"] == 2
        assert c0["int_composition"]["CYBINT"] == 2
        assert c0["risk_level"] == "high"  # max risk 7.5

        # Community 1 has 1 member
        c1 = next(c for c in communities if c["community_id"] == 1)
        assert c1["member_count"] == 1
        assert c1["int_composition"]["GEOINT"] == 1
        assert c1["risk_level"] == "low"

    @pytest.mark.asyncio
    async def test_detect_communities_empty(self, analyzer, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[])
        result = await analyzer.detect_communities_enhanced()
        assert result["community_count"] == 0

    @pytest.mark.asyncio
    async def test_get_community_details(self, analyzer, mock_client):
        mock_client.execute_read = AsyncMock(side_effect=[
            # First call: community members
            [
                {"id": "e1", "name": "A", "type": "ThreatActor",
                 "source_int": "CYBINT", "confidence": 0.8, "risk_score": 5.0},
                {"id": "e2", "name": "B", "type": "IPAddress",
                 "source_int": "CYBINT", "confidence": 0.9, "risk_score": 4.0},
            ],
            # Second call: internal relationships
            [
                {"source": "e1", "target": "e2", "type": "USES", "confidence": 0.7},
            ],
        ])

        result = await analyzer.get_community_details(0)
        assert result["member_count"] == 2
        assert len(result["internal_relationships"]) == 1
        assert result["internal_density"] > 0

    @pytest.mark.asyncio
    async def test_find_cross_community_bridges(self, analyzer, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[
            {"id": "bridge1", "name": "Bridge", "home_community": 0,
             "connected_communities": [1, 2], "bridge_count": 2},
        ])

        bridges = await analyzer.find_cross_community_bridges()
        assert len(bridges) == 1
        assert bridges[0]["entity_id"] == "bridge1"
        assert bridges[0]["bridge_count"] == 2


class TestTemporalAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return TemporalAnalyzer()

    def test_analyze_activity_patterns(self, analyzer):
        events = [
            {"timestamp": "2024-01-01T10:00:00Z"},
            {"timestamp": "2024-01-01T14:00:00Z"},
            {"timestamp": "2024-01-02T09:00:00Z"},
            {"timestamp": "2024-01-03T11:00:00Z"},
        ]
        result = analyzer.analyze_activity_patterns(events)
        assert result["total_events"] == 4
        assert len(result["bins"]) > 0

    def test_analyze_empty_events(self, analyzer):
        result = analyzer.analyze_activity_patterns([])
        assert result["total_events"] == 0

    def test_compute_burstiness(self, analyzer):
        events = [{"timestamp": f"2024-01-{i:02d}T10:00:00Z"} for i in range(1, 20)]
        result = analyzer.compute_burstiness(events)
        assert "burstiness" in result
        assert "interpretation" in result

    def test_compute_burstiness_insufficient_data(self, analyzer):
        events = [{"timestamp": "2024-01-01T10:00:00Z"}]
        result = analyzer.compute_burstiness(events)
        assert result["interpretation"] == "insufficient_data"

    def test_detect_periodicity(self, analyzer):
        events = [{"timestamp": f"2024-01-{i:02d}T10:00:00Z"} for i in range(1, 25)]
        result = analyzer.detect_periodicity(events)
        assert "periodic" in result
        assert "confidence" in result
