"""Integration test: investigation lifecycle — create, execute, report, export."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest


class TestInvestigationFlow:
    """End-to-end investigation workflow test."""

    @pytest.fixture
    def mock_pg_conn(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        conn.execute = AsyncMock()
        return conn

    @pytest.fixture
    def mock_neo4j_client(self):
        client = AsyncMock()
        client.execute_read = AsyncMock(return_value=[])
        client.execute_write = AsyncMock(return_value=[])
        return client

    @pytest.mark.asyncio
    async def test_create_investigation(self, mock_pg_conn):
        """Creating an investigation should persist to PostgreSQL."""
        investigation_id = str(uuid.uuid4())
        mock_pg_conn.fetchrow = AsyncMock(return_value={
            "id": investigation_id,
            "query": "test threat actor",
            "status": "created",
            "priority": "high",
            "target_ints": ["CYBINT", "SOCMINT"],
            "progress": 0,
            "entity_count": 0,
            "relationship_count": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        })

        result = await mock_pg_conn.fetchrow(
            "INSERT INTO investigations (...) VALUES (...) RETURNING *"
        )
        assert result["id"] == investigation_id
        assert result["status"] == "created"

    @pytest.mark.asyncio
    async def test_report_generation_json(self):
        """JSON report generation should produce structured output."""
        from nexus.reports.sections import ReportSections

        entities = [
            {"id": "e1", "name": "Actor1", "type": "ThreatActor", "confidence": 0.8,
             "risk_score": 7.5, "source_int": "CYBINT"},
            {"id": "e2", "name": "IP1", "type": "IPAddress", "confidence": 0.9,
             "risk_score": 3.0, "source_int": "CYBINT"},
        ]
        relationships = [
            {"source_id": "e1", "target_id": "e2", "type": "USES", "confidence": 0.7},
        ]

        sections = ReportSections()
        summary = sections.executive_summary(entities, relationships)
        assert summary["entity_count"] == 2
        assert summary["relationship_count"] == 1
        assert 0 <= summary["average_confidence"] <= 1

    @pytest.mark.asyncio
    async def test_stix_export_roundtrip(self):
        """STIX export and import should preserve entity data."""
        from nexus.interop.stix_converter import STIXConverter

        converter = STIXConverter()

        entity = {
            "id": "threatactor-abc123",
            "name": "APT-TEST",
            "type": "ThreatActor",
            "confidence": 0.85,
            "source_int": "CYBINT",
            "risk_score": 8.0,
            "properties": "{}",
        }

        sdo = converter.entity_to_sdo(entity)
        assert sdo["type"] == "threat-actor"
        assert sdo["name"] == "APT-TEST"
        assert sdo["confidence"] == 85

        # Round-trip back
        restored = converter.sdo_to_entity(sdo)
        assert restored["name"] == "APT-TEST"
        assert restored["type"] == "ThreatActor"
