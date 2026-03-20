"""Intelligence report generator — orchestrates section building and rendering."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from nexus.reports.sections import ReportSections
from nexus.reports.renderers.html_renderer import HTMLRenderer
from nexus.reports.renderers.pdf_renderer import PDFRenderer
from nexus.reports.renderers.json_renderer import JSONRenderer
from nexus.interop.stix_bundle import STIXBundleBuilder

logger = structlog.get_logger()


class ReportFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    STIX = "stix"


@dataclass
class ReportConfig:
    title: str
    investigation_id: str
    format: ReportFormat = ReportFormat.JSON
    include_sections: list[str] = field(default_factory=lambda: [
        "executive_summary",
        "entity_analysis",
        "relationship_graph",
        "timeline",
        "risk_assessment",
        "confidence_metrics",
        "conflict_notes",
        "recommendations",
    ])
    classification: str = "UNCLASSIFIED"


class ReportGenerator:
    """Orchestrates intelligence report generation."""

    def __init__(self) -> None:
        self._sections = ReportSections()
        self._html_renderer = HTMLRenderer()
        self._pdf_renderer = PDFRenderer()
        self._json_renderer = JSONRenderer()
        self._stix_builder = STIXBundleBuilder()

    def generate(
        self,
        config: ReportConfig,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        investigation: dict[str, Any] | None = None,
    ) -> dict[str, Any] | bytes | str:
        """Generate a report in the requested format.

        Returns:
            - dict for JSON/STIX formats
            - str for HTML format
            - bytes for PDF format
        """
        logger.info(
            "report.generating",
            investigation_id=config.investigation_id,
            format=config.format.value,
            sections=config.include_sections,
        )

        # Build report data from sections
        report_data = self._build_report_data(config, entities, relationships, investigation)

        # Render in requested format
        if config.format == ReportFormat.STIX:
            return self._stix_builder.build_investigation_bundle(
                investigation_id=config.investigation_id,
                entities=entities,
                relationships=relationships,
                report_summary=report_data.get("executive_summary", {}).get("summary", ""),
            )
        elif config.format == ReportFormat.HTML:
            return self._html_renderer.render(report_data)
        elif config.format == ReportFormat.PDF:
            return self._pdf_renderer.render(report_data)
        else:
            return self._json_renderer.render(report_data)

    def _build_report_data(
        self,
        config: ReportConfig,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        investigation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build structured report data from sections."""
        report: dict[str, Any] = {
            "title": config.title,
            "investigation_id": config.investigation_id,
            "classification": config.classification,
        }

        section_builders = {
            "executive_summary": lambda: self._sections.executive_summary(
                entities, relationships, investigation,
            ),
            "entity_analysis": lambda: self._sections.entity_analysis(entities),
            "relationship_graph": lambda: self._sections.relationship_graph_summary(
                entities, relationships,
            ),
            "timeline": lambda: self._sections.timeline_section(entities),
            "risk_assessment": lambda: self._sections.risk_assessment(entities),
            "confidence_metrics": lambda: self._sections.confidence_metrics(entities),
            "conflict_notes": lambda: self._sections.conflict_notes(entities),
            "recommendations": lambda: self._sections.recommendations(
                entities, relationships,
            ),
        }

        for section_name in config.include_sections:
            builder = section_builders.get(section_name)
            if builder:
                try:
                    report[section_name] = builder()
                except Exception as e:
                    logger.error("report.section_failed", section=section_name, error=str(e))
                    report[section_name] = {"error": str(e)}

        logger.info("report.generated", investigation_id=config.investigation_id)
        return report
