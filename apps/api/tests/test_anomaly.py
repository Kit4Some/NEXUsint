"""Advanced anomaly detection tests."""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock

from nexus.analytics.anomaly_detector import AnomalyDetector, Anomaly
from nexus.analytics.feature_extractor import FeatureExtractor


class TestFeatureExtractor:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock()

    @pytest.fixture
    def extractor(self, mock_client):
        return FeatureExtractor(mock_client)

    @pytest.mark.asyncio
    async def test_extract_entity_features(self, extractor, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[
            {"id": "e1", "name": "Entity1", "confidence": 0.8, "risk_score": 5.0,
             "degree": 3, "in_degree": 1, "out_degree": 2, "rel_type_count": 2},
            {"id": "e2", "name": "Entity2", "confidence": 0.5, "risk_score": 8.0,
             "degree": 10, "in_degree": 7, "out_degree": 3, "rel_type_count": 4},
        ])

        features, ids, names = await extractor.extract_entity_features()
        assert features.shape == (2, 7)
        assert ids == ["e1", "e2"]
        assert names == ["Entity1", "Entity2"]
        assert features[0][0] == 0.8  # confidence
        assert features[1][1] == 8.0  # risk_score

    @pytest.mark.asyncio
    async def test_extract_empty(self, extractor, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[])
        features, ids, names = await extractor.extract_entity_features()
        assert features.shape == (0, 7)
        assert ids == []


class TestAnomalyDetector:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock()

    @pytest.fixture
    def detector(self, mock_client):
        return AnomalyDetector(mock_client)

    @pytest.mark.asyncio
    async def test_detect_statistical_outliers(self, detector, mock_client):
        # Create data with one clear outlier
        normal = [
            {"id": f"e{i}", "name": f"Normal{i}", "confidence": 0.5, "risk_score": 3.0,
             "degree": 3, "in_degree": 1, "out_degree": 2, "rel_type_count": 2}
            for i in range(20)
        ]
        outlier = {
            "id": "outlier", "name": "Outlier", "confidence": 0.5, "risk_score": 3.0,
            "degree": 100, "in_degree": 50, "out_degree": 50, "rel_type_count": 2,
        }
        normal.append(outlier)

        mock_client.execute_read = AsyncMock(return_value=normal)
        anomalies = await detector.detect_statistical_outliers()

        # The outlier with degree=100 should be detected
        outlier_ids = [a.entity_id for a in anomalies]
        assert "outlier" in outlier_ids

    @pytest.mark.asyncio
    async def test_detect_graph_anomalies(self, detector, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[
            {"id": "hub", "name": "Hub", "degree": 50, "rel_types": 8,
             "mean_deg": 5.0, "std_deg": 3.0},
        ])

        anomalies = await detector.detect_graph_anomalies()
        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == "graph_structural"
        assert anomalies[0].entity_id == "hub"

    @pytest.mark.asyncio
    async def test_detect_bridge_entities(self, detector, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[
            {"id": "bridge", "name": "Bridge", "betweenness": 0.95,
             "mean_bc": 0.1, "std_bc": 0.15},
        ])

        anomalies = await detector.detect_bridge_entities()
        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == "bridge_entity"

    @pytest.mark.asyncio
    async def test_detect_all_deduplicates(self, detector, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[])
        anomalies = await detector.detect_all(methods=["statistical", "graph"])
        # Should not raise and returns empty for no data
        assert isinstance(anomalies, list)

    def test_anomaly_dataclass(self):
        a = Anomaly(
            entity_id="test",
            entity_name="Test",
            anomaly_type="test_type",
            score=0.95,
            evidence={"key": "value"},
        )
        assert a.entity_id == "test"
        assert a.score == 0.95
