"""PDF report renderer using ReportLab."""

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


class PDFRenderer:
    """Renders intelligence reports as PDF documents."""

    def __init__(self) -> None:
        self._styles = getSampleStyleSheet()
        self._styles.add(ParagraphStyle(
            name="Classification",
            parent=self._styles["Heading1"],
            textColor=colors.red,
            alignment=1,  # center
            fontSize=10,
        ))
        self._styles.add(ParagraphStyle(
            name="SectionTitle",
            parent=self._styles["Heading2"],
            spaceBefore=12,
            spaceAfter=6,
        ))

    def render(self, report_data: dict[str, Any]) -> bytes:
        """Render report data to PDF bytes."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
        )

        elements: list[Any] = []
        classification = report_data.get("classification", "UNCLASSIFIED")

        # Classification header
        elements.append(Paragraph(classification, self._styles["Classification"]))
        elements.append(Spacer(1, 6 * mm))

        # Title
        title = report_data.get("title", "Intelligence Report")
        elements.append(Paragraph(title, self._styles["Title"]))
        elements.append(Paragraph(
            f"Investigation: {report_data.get('investigation_id', 'N/A')}",
            self._styles["Normal"],
        ))
        elements.append(Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            self._styles["Normal"],
        ))
        elements.append(Spacer(1, 10 * mm))

        # Executive Summary
        if "executive_summary" in report_data:
            elements.extend(self._render_executive_summary(report_data["executive_summary"]))

        # Entity Analysis
        if "entity_analysis" in report_data:
            elements.extend(self._render_entity_analysis(report_data["entity_analysis"]))

        # Risk Assessment
        if "risk_assessment" in report_data:
            elements.extend(self._render_risk_assessment(report_data["risk_assessment"]))

        # Confidence Metrics
        if "confidence_metrics" in report_data:
            elements.extend(self._render_confidence_metrics(report_data["confidence_metrics"]))

        # Recommendations
        if "recommendations" in report_data:
            elements.extend(self._render_recommendations(report_data["recommendations"]))

        # Footer classification
        elements.append(Spacer(1, 10 * mm))
        elements.append(Paragraph(classification, self._styles["Classification"]))

        doc.build(elements)
        return buffer.getvalue()

    def _render_executive_summary(self, data: dict[str, Any]) -> list[Any]:
        elements: list[Any] = []
        elements.append(Paragraph("Executive Summary", self._styles["SectionTitle"]))
        elements.append(Paragraph(data.get("summary", ""), self._styles["Normal"]))
        elements.append(Spacer(1, 4 * mm))

        # Key metrics table
        metrics = [
            ["Metric", "Value"],
            ["Entities", str(data.get("entity_count", 0))],
            ["Relationships", str(data.get("relationship_count", 0))],
            ["Avg Confidence", f"{data.get('average_confidence', 0):.1%}"],
            ["High-Risk Entities", str(data.get("high_risk_entity_count", 0))],
        ]
        table = Table(metrics, colWidths=[120, 100])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 6 * mm))
        return elements

    def _render_entity_analysis(self, data: dict[str, Any]) -> list[Any]:
        elements: list[Any] = []
        elements.append(PageBreak())
        elements.append(Paragraph("Entity Analysis", self._styles["SectionTitle"]))

        for entity_type, entities in data.get("groups", {}).items():
            elements.append(Paragraph(f"{entity_type} ({len(entities)})", self._styles["Heading3"]))
            rows = [["Name", "Confidence", "Risk", "Source", "Grade"]]
            for e in entities[:20]:
                rows.append([
                    e.get("name", "")[:40],
                    f"{e.get('confidence', 0):.1%}",
                    f"{e.get('risk_score', 0):.1f}",
                    e.get("source_int", ""),
                    e.get("reliability_grade", ""),
                ])
            table = Table(rows, colWidths=[150, 70, 50, 60, 40])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 4 * mm))

        return elements

    def _render_risk_assessment(self, data: dict[str, Any]) -> list[Any]:
        elements: list[Any] = []
        elements.append(Paragraph("Risk Assessment", self._styles["SectionTitle"]))

        dist = data.get("risk_distribution", {})
        rows = [["Risk Level", "Count", "Percentage"]]
        for level in ["critical", "high", "medium", "low"]:
            count = dist.get(level, 0)
            pct = data.get("risk_percentages", {}).get(level, 0)
            rows.append([level.capitalize(), str(count), f"{pct}%"])

        table = Table(rows, colWidths=[100, 80, 80])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c0392b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 6 * mm))
        return elements

    def _render_confidence_metrics(self, data: dict[str, Any]) -> list[Any]:
        elements: list[Any] = []
        elements.append(Paragraph("Confidence Metrics", self._styles["SectionTitle"]))
        elements.append(Paragraph(
            f"Overall average confidence: {data.get('overall_average', 0):.1%}",
            self._styles["Normal"],
        ))

        by_int = data.get("confidence_by_int", {})
        if by_int:
            rows = [["INT Source", "Avg Confidence", "Entity Count"]]
            counts = data.get("entity_count_by_int", {})
            for source, avg in sorted(by_int.items()):
                rows.append([source, f"{avg:.1%}", str(counts.get(source, 0))])
            table = Table(rows, colWidths=[100, 100, 80])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2980b9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)

        elements.append(Spacer(1, 6 * mm))
        return elements

    def _render_recommendations(self, data: dict[str, Any]) -> list[Any]:
        elements: list[Any] = []
        elements.append(Paragraph("Recommendations", self._styles["SectionTitle"]))

        for rec in data.get("recommendations", []):
            priority = rec.get("priority", "").upper()
            text = f"[{priority}] {rec.get('recommendation', '')}"
            elements.append(Paragraph(f"• {text}", self._styles["Normal"]))
            elements.append(Spacer(1, 2 * mm))

        return elements
