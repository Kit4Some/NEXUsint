"""STIX 2.1 converter and bundle tests."""

import pytest
from unittest.mock import AsyncMock

from nexus.interop.stix_converter import STIXConverter
from nexus.interop.stix_bundle import STIXBundleBuilder, STIXBundleImporter


class TestSTIXConverter:
    @pytest.fixture
    def converter(self):
        return STIXConverter()

    def test_entity_to_sdo_threat_actor(self, converter):
        entity = {
            "id": "ta-001",
            "type": "ThreatActor",
            "name": "APT29",
            "confidence": 0.85,
            "sourceInt": "CYBINT",
            "riskScore": 8.5,
            "properties": {"types": ["nation-state"]},
        }
        sdo = converter.entity_to_sdo(entity)
        assert sdo is not None
        assert sdo["type"] == "threat-actor"
        assert sdo["spec_version"] == "2.1"
        assert sdo["name"] == "APT29"
        assert sdo["x_nexus_id"] == "ta-001"
        assert sdo["x_nexus_source_int"] == "CYBINT"
        assert sdo["id"].startswith("threat-actor--")

    def test_entity_to_sdo_ip_address(self, converter):
        entity = {
            "id": "ip-001",
            "type": "IPAddress",
            "name": "192.168.1.1",
            "confidence": 0.9,
            "sourceInt": "CYBINT",
            "properties": {"address": "192.168.1.1"},
        }
        sdo = converter.entity_to_sdo(entity)
        assert sdo is not None
        assert sdo["type"] == "ipv4-addr"
        assert sdo["value"] == "192.168.1.1"

    def test_entity_to_sdo_location(self, converter):
        entity = {
            "id": "loc-001",
            "type": "Location",
            "name": "Seoul",
            "latitude": 37.5665,
            "longitude": 126.978,
            "confidence": 0.8,
            "sourceInt": "GEOINT",
            "properties": {"country": "South Korea"},
        }
        sdo = converter.entity_to_sdo(entity)
        assert sdo is not None
        assert sdo["type"] == "location"
        assert sdo["latitude"] == 37.5665
        assert sdo["country"] == "South Korea"

    def test_entity_to_sdo_unsupported_type(self, converter):
        entity = {
            "id": "unknown-001",
            "type": "UnknownType",
            "name": "test",
        }
        sdo = converter.entity_to_sdo(entity)
        assert sdo is None

    def test_relationship_to_sro(self, converter):
        rel = {
            "id": "rel-001",
            "type": "ATTRIBUTED_TO",
            "confidence": 0.75,
        }
        sro = converter.relationship_to_sro(
            rel,
            "threat-actor--abc",
            "identity--def",
        )
        assert sro is not None
        assert sro["type"] == "relationship"
        assert sro["relationship_type"] == "attributed-to"
        assert sro["source_ref"] == "threat-actor--abc"
        assert sro["target_ref"] == "identity--def"
        assert sro["confidence"] == 75

    def test_relationship_to_sro_unsupported(self, converter):
        rel = {"type": "UNKNOWN_REL"}
        sro = converter.relationship_to_sro(rel, "a", "b")
        assert sro is None

    def test_sdo_roundtrip(self, converter):
        entity = {
            "id": "ta-round",
            "type": "ThreatActor",
            "name": "TestActor",
            "confidence": 0.7,
            "sourceInt": "CYBINT",
            "riskScore": 5.0,
            "properties": {"types": ["hacktivist"]},
        }
        sdo = converter.entity_to_sdo(entity)
        assert sdo is not None

        restored = converter.sdo_to_entity(sdo)
        assert restored["name"] == "TestActor"
        assert restored["type"] == "ThreatActor"
        assert restored["id"] == "ta-round"
        assert abs(restored["confidence"] - 0.7) < 0.01

    def test_deterministic_ids(self, converter):
        """Same NEXUS ID should always produce the same STIX ID."""
        id1 = converter._generate_stix_id("threat-actor", "ta-001")
        id2 = converter._generate_stix_id("threat-actor", "ta-001")
        assert id1 == id2
        assert id1.startswith("threat-actor--")


class TestSTIXBundle:
    @pytest.fixture
    def builder(self):
        return STIXBundleBuilder()

    @pytest.fixture
    def importer(self):
        return STIXBundleImporter()

    def test_build_bundle(self, builder):
        entities = [
            {"id": "ta-1", "type": "ThreatActor", "name": "APT1",
             "confidence": 0.8, "sourceInt": "CYBINT"},
            {"id": "ip-1", "type": "IPAddress", "name": "1.2.3.4",
             "confidence": 0.9, "sourceInt": "CYBINT",
             "properties": {"address": "1.2.3.4"}},
        ]
        relationships = [
            {"source_id": "ta-1", "target_id": "ip-1",
             "type": "USES", "confidence": 0.7},
        ]

        bundle = builder.build_bundle(entities, relationships)
        assert bundle["type"] == "bundle"
        assert bundle["spec_version"] == "2.1"
        assert bundle["id"].startswith("bundle--")
        assert len(bundle["objects"]) == 3  # 2 SDOs + 1 SRO

    def test_bundle_has_correct_spec_version(self, builder):
        bundle = builder.build_bundle([], [])
        assert bundle["spec_version"] == "2.1"
        assert bundle["type"] == "bundle"

    def test_build_investigation_bundle_with_report(self, builder):
        entities = [
            {"id": "ta-1", "type": "ThreatActor", "name": "APT1",
             "confidence": 0.8, "sourceInt": "CYBINT"},
        ]
        bundle = builder.build_investigation_bundle(
            "inv-123", entities, [],
            report_summary="Test investigation summary",
        )
        report_sdos = [o for o in bundle["objects"] if o["type"] == "report"]
        assert len(report_sdos) == 1
        assert report_sdos[0]["name"] == "NEXUS Investigation inv-123"
        assert report_sdos[0]["x_nexus_investigation_id"] == "inv-123"

    def test_parse_bundle(self, importer):
        bundle = {
            "type": "bundle",
            "id": "bundle--test",
            "spec_version": "2.1",
            "objects": [
                {
                    "type": "threat-actor",
                    "spec_version": "2.1",
                    "id": "threat-actor--abc",
                    "name": "TestActor",
                    "created": "2024-01-01T00:00:00Z",
                    "modified": "2024-01-01T00:00:00Z",
                },
                {
                    "type": "ipv4-addr",
                    "spec_version": "2.1",
                    "id": "ipv4-addr--def",
                    "value": "10.0.0.1",
                    "created": "2024-01-01T00:00:00Z",
                    "modified": "2024-01-01T00:00:00Z",
                },
                {
                    "type": "relationship",
                    "spec_version": "2.1",
                    "id": "relationship--ghi",
                    "relationship_type": "uses",
                    "source_ref": "threat-actor--abc",
                    "target_ref": "ipv4-addr--def",
                    "confidence": 80,
                    "created": "2024-01-01T00:00:00Z",
                    "modified": "2024-01-01T00:00:00Z",
                },
            ],
        }

        entities, relationships = importer.parse_bundle(bundle)
        assert len(entities) == 2
        assert len(relationships) == 1
        assert entities[0]["type"] == "ThreatActor"
        assert entities[1]["type"] == "IPAddress"
        assert relationships[0]["type"] == "USES"

    @pytest.mark.asyncio
    async def test_import_bundle(self, importer):
        bundle = {
            "type": "bundle",
            "id": "bundle--test",
            "spec_version": "2.1",
            "objects": [
                {
                    "type": "threat-actor",
                    "spec_version": "2.1",
                    "id": "threat-actor--abc",
                    "name": "Imported Actor",
                    "created": "2024-01-01T00:00:00Z",
                    "modified": "2024-01-01T00:00:00Z",
                },
            ],
        }

        mock_repo = AsyncMock()
        mock_repo.create_entity = AsyncMock()
        mock_repo.create_relationship = AsyncMock()

        result = await importer.import_bundle(bundle, mock_repo)
        assert result["entities_created"] == 1
        assert result["relationships_created"] == 0
        assert len(result["errors"]) == 0
        mock_repo.create_entity.assert_called_once()
