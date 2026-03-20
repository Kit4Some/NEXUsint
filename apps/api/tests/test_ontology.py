"""Ontology bridge and SHACL validation tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from nexus.knowledge.ontology_bridge import OntologyBridge
from nexus.knowledge.shacl_validator import SHACLValidator, ValidationResult


# --- OntologyBridge Tests ---


class TestOntologyBridge:
    @pytest.fixture
    def mock_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def bridge(self, mock_client):
        return OntologyBridge(mock_client)

    @pytest.mark.asyncio
    async def test_initialize_n10s(self, bridge, mock_client):
        mock_client.execute_write = AsyncMock(return_value=[])
        await bridge.initialize_n10s()
        # Should call execute_write multiple times (constraint + config + prefixes)
        assert mock_client.execute_write.call_count >= 2

    @pytest.mark.asyncio
    async def test_import_ontology_inline(self, bridge, mock_client):
        mock_client.execute_write = AsyncMock(
            return_value=[{"triplesLoaded": 42, "namespaces": 5}]
        )
        result = await bridge.import_ontology(owl_content="<rdf:RDF></rdf:RDF>")
        assert result["triplesLoaded"] == 42

    @pytest.mark.asyncio
    async def test_import_rdf(self, bridge, mock_client):
        mock_client.execute_write = AsyncMock(
            return_value=[{"triplesLoaded": 10}]
        )
        result = await bridge.import_rdf("@prefix nexus: <http://nexus-osint.org/ontology#> .")
        assert result["triplesLoaded"] == 10

    @pytest.mark.asyncio
    async def test_export_entity_rdf(self, bridge, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[{"rdf": "@prefix nexus: ..."}])
        rdf = await bridge.export_entity_rdf("entity-123", depth=1)
        assert rdf == "@prefix nexus: ..."

    @pytest.mark.asyncio
    async def test_get_ontology_classes(self, bridge, mock_client):
        mock_client.execute_read = AsyncMock(
            return_value=[
                {"uri": "http://nexus-osint.org/ontology#Person", "label": "Person",
                 "comment": None, "subclasses": [], "superclasses": ["Entity"]},
                {"uri": "http://nexus-osint.org/ontology#Location", "label": "Location",
                 "comment": None, "subclasses": [], "superclasses": ["Entity"]},
            ]
        )
        classes = await bridge.get_ontology_classes()
        assert len(classes) == 2
        assert classes[0]["label"] == "Person"

    @pytest.mark.asyncio
    async def test_get_ontology_properties(self, bridge, mock_client):
        mock_client.execute_read = AsyncMock(
            return_value=[
                {"uri": "http://nexus-osint.org/ontology#confidence", "label": "confidence",
                 "types": ["Property", "DatatypeProperty"], "domain": ["Entity"], "range": ["float"]},
            ]
        )
        props = await bridge.get_ontology_properties()
        assert len(props) == 1
        assert props[0]["label"] == "confidence"

    @pytest.mark.asyncio
    async def test_ontology_aware_search(self, bridge, mock_client):
        # First call: subclass query
        # Second call: entity search
        mock_client.execute_read = AsyncMock(
            side_effect=[
                [{"labels": ["Person", "ThreatActor"]}],
                [{"entity": {"id": "p-1", "name": "Test Person"}}],
            ]
        )
        results = await bridge.ontology_aware_search("Person")
        assert len(results) == 1


# --- SHACLValidator Tests ---


class TestSHACLValidator:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock()

    @pytest.fixture
    def validator(self, mock_client):
        return SHACLValidator(mock_client)

    @pytest.mark.asyncio
    async def test_validate_entity_missing(self, validator, mock_client):
        mock_client.execute_read = AsyncMock(return_value=[])
        result = await validator.validate_entity("nonexistent")
        assert not result.conforms
        assert result.violation_count == 1

    @pytest.mark.asyncio
    async def test_validate_entity_valid(self, validator, mock_client):
        mock_client.execute_read = AsyncMock(
            return_value=[{
                "entity": {
                    "id": "e-1",
                    "confidence": 0.8,
                    "sourceInt": "CYBINT",
                    "riskScore": 5.0,
                    "__labels": ["Entity", "Person"],
                    "name": "John Doe",
                }
            }]
        )
        result = await validator.validate_entity("e-1")
        assert result.conforms
        assert result.violation_count == 0

    @pytest.mark.asyncio
    async def test_validate_entity_missing_source_int(self, validator, mock_client):
        mock_client.execute_read = AsyncMock(
            return_value=[{
                "entity": {
                    "id": "e-2",
                    "confidence": 0.5,
                    "__labels": ["Entity"],
                }
            }]
        )
        result = await validator.validate_entity("e-2")
        assert not result.conforms
        violations = [v for v in result.violations if v["path"] == "sourceInt"]
        assert len(violations) == 1

    @pytest.mark.asyncio
    async def test_validate_entity_confidence_out_of_range(self, validator, mock_client):
        mock_client.execute_read = AsyncMock(
            return_value=[{
                "entity": {
                    "id": "e-3",
                    "confidence": 1.5,
                    "sourceInt": "CYBINT",
                    "__labels": ["Entity"],
                }
            }]
        )
        result = await validator.validate_entity("e-3")
        assert not result.conforms
        violations = [v for v in result.violations if v["path"] == "confidence"]
        assert len(violations) == 1

    @pytest.mark.asyncio
    async def test_validate_location_missing_lat(self, validator, mock_client):
        mock_client.execute_read = AsyncMock(
            return_value=[{
                "entity": {
                    "id": "loc-1",
                    "sourceInt": "GEOINT",
                    "confidence": 0.8,
                    "longitude": 126.978,
                    "__labels": ["Entity", "Location"],
                }
            }]
        )
        result = await validator.validate_entity("loc-1")
        # Location without latitude should have violations
        assert not result.conforms

    @pytest.mark.asyncio
    async def test_validate_all(self, validator, mock_client):
        mock_client.execute_read = AsyncMock(
            return_value=[
                {"entity": {"id": "e-1", "confidence": 0.8, "sourceInt": "CYBINT",
                             "__labels": ["Entity"]}, "entity_id": "e-1"},
                {"entity": {"id": "e-2", "confidence": 0.5, "__labels": ["Entity"]},
                 "entity_id": "e-2"},
            ]
        )
        result = await validator.validate_all(limit=100)
        assert result.entity_count_checked == 2
        # e-2 is missing sourceInt
        assert result.violation_count >= 1

    @pytest.mark.asyncio
    async def test_validate_relationships(self, validator, mock_client):
        mock_client.execute_read = AsyncMock(
            return_value=[
                {
                    "source_id": "d-1",
                    "source_labels": ["Domain"],
                    "target_id": "p-1",
                    "target_labels": ["Person"],  # Should be IPAddress
                    "rel_type": "RESOLVES_TO",
                }
            ]
        )
        result = await validator.validate_relationships()
        assert not result.conforms
        assert result.violation_count >= 1


class TestValidationResult:
    def test_to_dict(self):
        vr = ValidationResult(
            conforms=False,
            violations=[{"entity_id": "e-1", "path": "sourceInt", "message": "missing"}],
            violation_count=1,
            entity_count_checked=1,
        )
        d = vr.to_dict()
        assert d["conforms"] is False
        assert d["violation_count"] == 1
        assert len(d["violations"]) == 1
