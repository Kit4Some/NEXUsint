"""Tests for Prometheus metrics middleware and application metrics."""

import pytest
from unittest.mock import AsyncMock

from nexus.api.middleware.metrics import _normalize_path


class TestPathNormalization:
    def test_simple_path(self):
        assert _normalize_path("/api/v1/entities") == "/api/v1/entities"

    def test_uuid_path(self):
        result = _normalize_path("/api/v1/entities/550e8400-e29b-41d4-a716-446655440000")
        assert "{id}" in result

    def test_hex_id_path(self):
        result = _normalize_path("/api/v1/entities/threatactor-a1b2c3d4e5f6")
        assert "{id}" in result

    def test_short_segments_unchanged(self):
        result = _normalize_path("/api/v1/auth/login")
        assert result == "/api/v1/auth/login"


class TestApplicationMetrics:
    def test_metrics_importable(self):
        from nexus.services.metrics import (
            entities_total,
            investigations_active,
            collection_jobs_total,
            cache_hits_total,
            cache_misses_total,
            neo4j_query_duration,
            websocket_connections,
            anomalies_detected,
        )
        # Verify all metrics are importable and have correct types
        assert entities_total._type == "gauge"
        assert investigations_active._type == "gauge"
        assert collection_jobs_total._type == "counter"
        assert cache_hits_total._type == "counter"
        assert neo4j_query_duration._type == "histogram"
        assert websocket_connections._type == "gauge"
        assert anomalies_detected._type == "counter"

    def test_counter_increment(self):
        from nexus.services.metrics import collection_jobs_total
        before = collection_jobs_total.labels(int_type="CYBINT", status="completed")._value.get()
        collection_jobs_total.labels(int_type="CYBINT", status="completed").inc()
        after = collection_jobs_total.labels(int_type="CYBINT", status="completed")._value.get()
        assert after == before + 1

    def test_gauge_set(self):
        from nexus.services.metrics import entities_total
        entities_total.set(42)
        assert entities_total._value.get() == 42

    def test_histogram_observe(self):
        from nexus.services.metrics import neo4j_query_duration
        neo4j_query_duration.labels(query_type="read").observe(0.05)
        # Histogram observe should not raise
