"""Intelligence report generation tests."""

import pytest

from nexus.reports.generator import ReportGenerator, ReportConfig, ReportFormat
from nexus.reports.sections import ReportSections
from nexus.reports.renderers.json_renderer import JSONRenderer
from nexus.reports.renderers.html_renderer import HTMLRenderer


@pytest.fixture
def sample_entities():
    return [
        {
            "id": "ta-1", "type": "ThreatActor", "name": "APT29",
            "confidence": 0.85, "sourceInt": "CYBINT", "riskScore": 8.5,
            "created_at": "2024-01-15T10:00:00Z",
        },
        {
            "id": "ip-1", "type": "IPAddress", "name": "10.0.0.1",
            "confidence": 0.9, "sourceInt": "CYBINT", "riskScore": 6.0,
            "properties": {"address": "10.0.0.1"},
            "created_at": "2024-01-16T08:00:00Z",
        },
        {
            "id": "loc-1", "type": "Location", "name": "Seoul",
            "confidence": 0.7, "sourceInt": "GEOINT", "riskScore": 2.0,
            "created_at": "2024-01-17T12:00:00Z",
        },
        {
            "id": "mal-1", "type": "Malware", "name": "CozyBear RAT",
            "confidence": 0.4, "sourceInt": "CYBINT", "riskScore": 9.5,
            "created_at": "2024-01-18T06:00:00Z",
        },
    ]


@pytest.fixture
def sample_relationships():
    return [
        {"source_id": "ta-1", "target_id": "ip-1", "type": "USES", "confidence": 0.8},
        {"source_id": "ta-1", "target_id": "mal-1", "type": "USES", "confidence": 0.75},
        {"source_id": "ta-1", "target_id": "loc-1", "type": "LOCATED_AT", "confidence": 0.6},
    ]


class TestReportSections:
    @pytest.fixture
    def sections(self):
        return ReportSections()

    def test_executive_summary(self, sections, sample_entities, sample_relationships):
        result = sections.executive_summary(sample_entities, sample_relationships, None)
        assert result["entity_count"] == 4
        assert result["relationship_count"] == 3
        assert "ThreatActor" in result["entity_type_breakdown"]
        assert result["high_risk_entity_count"] == 2  # riskScore >= 7.0
        assert "summary" in result

    def test_executive_summary_with_investigation(self, sections, sample_entities, sample_relationships):
        inv = {"query": "APT29 infrastructure", "status": "completed", "target_ints": ["CYBINT"]}
        result = sections.executive_summary(sample_entities, sample_relationships, inv)
        assert result["query"] == "APT29 infrastructure"

    def test_entity_analysis(self, sections, sample_entities):
        result = sections.entity_analysis(sample_entities)
        assert result["total_types"] == 4
        assert "ThreatActor" in result["groups"]
        assert result["groups"]["ThreatActor"][0]["name"] == "APT29"

    def test_relationship_graph_summary(self, sections, sample_entities, sample_relationships):
        result = sections.relationship_graph_summary(sample_entities, sample_relationships)
        assert result["node_count"] == 4
        assert result["edge_count"] == 3
        assert "USES" in result["relationship_type_breakdown"]
        assert result["top_connected_nodes"][0]["id"] == "ta-1"  # highest degree

    def test_timeline_section(self, sections, sample_entities):
        result = sections.timeline_section(sample_entities)
        assert result["event_count"] == 4
        assert result["earliest"] == "2024-01-15T10:00:00Z"
        assert result["latest"] == "2024-01-18T06:00:00Z"

    def test_risk_assessment(self, sections, sample_entities):
        result = sections.risk_assessment(sample_entities)
        assert result["risk_distribution"]["critical"] == 1  # mal-1 (9.5)
        assert result["risk_distribution"]["high"] == 1     # ta-1 (8.5)
        assert result["risk_distribution"]["medium"] == 1   # ip-1 (6.0)
        assert result["risk_distribution"]["low"] == 1      # loc-1 (2.0)
        assert len(result["critical_entities"]) == 1
        assert result["critical_entities"][0]["name"] == "CozyBear RAT"

    def test_confidence_metrics(self, sections, sample_entities):
        result = sections.confidence_metrics(sample_entities)
        assert "admiralty_grade_distribution" in result
        assert result["entity_count_by_int"]["CYBINT"] == 3
        assert result["entity_count_by_int"]["GEOINT"] == 1

    def test_conflict_notes_low_confidence(self, sections, sample_entities):
        result = sections.conflict_notes(sample_entities)
        # mal-1 has confidence 0.4 which is >= 0.3, so no low-conf entries by default
        # Let's check the structure is correct
        assert "conflicting_entities" in result
        assert "low_confidence_entities" in result

    def test_recommendations_isolated_entities(self, sections):
        entities = [
            {"id": "e1", "name": "A", "confidence": 0.8, "riskScore": 3.0, "sourceInt": "CYBINT"},
            {"id": "e2", "name": "B", "confidence": 0.5, "riskScore": 3.0, "sourceInt": "CYBINT"},
        ]
        rels: list = []
        result = sections.recommendations(entities, rels)
        # Both entities are isolated
        rec_texts = [r["recommendation"] for r in result["recommendations"]]
        assert any("no relationships" in r for r in rec_texts)

    def test_recommendations_uncertain_risks(self, sections):
        entities = [
            {"id": "e1", "name": "RiskyThing", "confidence": 0.3, "riskScore": 8.0, "sourceInt": "CYBINT"},
        ]
        result = sections.recommendations(entities, [])
        rec_texts = [r["recommendation"] for r in result["recommendations"]]
        assert any("verification" in r.lower() for r in rec_texts)


class TestJSONRenderer:
    def test_render(self):
        renderer = JSONRenderer()
        data = {"title": "Test Report", "investigation_id": "inv-1", "classification": "UNCLASSIFIED"}
        result = renderer.render(data)
        assert result["format"] == "json"
        assert result["title"] == "Test Report"
        assert "generated_at" in result

    def test_render_excludes_meta_from_sections(self):
        renderer = JSONRenderer()
        data = {
            "title": "Test",
            "investigation_id": "inv-1",
            "classification": "UNCLASSIFIED",
            "executive_summary": {"summary": "hello"},
        }
        result = renderer.render(data)
        assert "executive_summary" in result["sections"]
        assert "title" not in result["sections"]


class TestHTMLRenderer:
    def test_render(self):
        renderer = HTMLRenderer()
        data = {
            "title": "Test Report",
            "investigation_id": "inv-1",
            "classification": "SECRET",
            "executive_summary": {
                "summary": "Test summary",
                "entity_count": 10,
                "relationship_count": 5,
                "average_confidence": 0.75,
                "high_risk_entity_count": 2,
            },
        }
        html = renderer.render(data)
        assert "<!DOCTYPE html>" in html
        assert "Test Report" in html
        assert "SECRET" in html
        assert "Test summary" in html


class TestReportGenerator:
    def test_generate_json(self, sample_entities, sample_relationships):
        generator = ReportGenerator()
        config = ReportConfig(
            title="Test Report",
            investigation_id="inv-test",
            format=ReportFormat.JSON,
        )
        result = generator.generate(config, sample_entities, sample_relationships)
        assert isinstance(result, dict)
        assert result["title"] == "Test Report"

    def test_generate_html(self, sample_entities, sample_relationships):
        generator = ReportGenerator()
        config = ReportConfig(
            title="HTML Report",
            investigation_id="inv-html",
            format=ReportFormat.HTML,
        )
        result = generator.generate(config, sample_entities, sample_relationships)
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result

    def test_generate_stix(self, sample_entities, sample_relationships):
        generator = ReportGenerator()
        config = ReportConfig(
            title="STIX Report",
            investigation_id="inv-stix",
            format=ReportFormat.STIX,
        )
        result = generator.generate(config, sample_entities, sample_relationships)
        assert isinstance(result, dict)
        assert result["type"] == "bundle"
        assert result["spec_version"] == "2.1"

    def test_generate_with_subset_sections(self, sample_entities, sample_relationships):
        generator = ReportGenerator()
        config = ReportConfig(
            title="Partial Report",
            investigation_id="inv-partial",
            format=ReportFormat.JSON,
            include_sections=["executive_summary", "risk_assessment"],
        )
        result = generator.generate(config, sample_entities, sample_relationships)
        sections = result["sections"]
        assert "executive_summary" in sections
        assert "risk_assessment" in sections
        assert "entity_analysis" not in sections
