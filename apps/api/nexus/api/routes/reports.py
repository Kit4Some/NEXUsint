"""Intelligence report generation routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from nexus.dependencies import get_neo4j
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.reports.generator import ReportGenerator, ReportConfig, ReportFormat

router = APIRouter()

_generator = ReportGenerator()


async def _fetch_investigation_data(
    client: Neo4jClient,
    investigation_id: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch investigation metadata, entities, and relationships."""
    # Investigation metadata
    inv_results = await client.execute_read(
        """
        MATCH (i:Investigation {id: $invId})
        RETURN i {.*} AS investigation
        """,
        {"invId": investigation_id},
    )
    investigation = inv_results[0]["investigation"] if inv_results else None

    # Entities
    entities = await client.execute_read(
        """
        MATCH (e)
        WHERE e.investigationId = $invId AND e.id IS NOT NULL
        RETURN e {.*, type: head(labels(e))} AS entity
        LIMIT 500
        """,
        {"invId": investigation_id},
    )

    # Relationships
    relationships = await client.execute_read(
        """
        MATCH (a)-[r]->(b)
        WHERE a.investigationId = $invId OR b.investigationId = $invId
        RETURN a.id AS source_id, b.id AS target_id,
               type(r) AS type, r.confidence AS confidence
        LIMIT 1000
        """,
        {"invId": investigation_id},
    )

    entity_list = [e["entity"] for e in entities if e.get("entity")]
    rel_list = [dict(r) for r in relationships]

    return investigation, entity_list, rel_list


@router.post("/generate/{investigation_id}")
async def generate_report(
    investigation_id: str,
    format: str = Query("json", pattern="^(json|html|pdf|stix)$"),
    sections: str | None = Query(None, description="Comma-separated section names"),
    title: str | None = Query(None),
    classification: str = Query("UNCLASSIFIED"),
    driver=Depends(get_neo4j),
) -> Any:
    """Generate an intelligence report for an investigation."""
    client = Neo4jClient(driver)
    investigation, entities, relationships = await _fetch_investigation_data(
        client, investigation_id,
    )

    if not entities and not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found or has no data")

    report_format = ReportFormat(format)
    include_sections = (
        [s.strip() for s in sections.split(",") if s.strip()]
        if sections else None
    )

    config = ReportConfig(
        title=title or f"Intelligence Report — {investigation_id}",
        investigation_id=investigation_id,
        format=report_format,
    )
    if include_sections:
        config.include_sections = include_sections
    config.classification = classification

    result = _generator.generate(config, entities, relationships, investigation)

    if report_format == ReportFormat.HTML:
        return HTMLResponse(content=result)
    elif report_format == ReportFormat.PDF:
        return Response(
            content=result,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=report-{investigation_id}.pdf"},
        )
    else:
        return result


@router.get("/{investigation_id}")
async def get_report(
    investigation_id: str,
    format: str = Query("json", pattern="^(json|html|pdf|stix)$"),
    driver=Depends(get_neo4j),
) -> Any:
    """Get a report for an investigation (shorthand for generate with defaults)."""
    client = Neo4jClient(driver)
    investigation, entities, relationships = await _fetch_investigation_data(
        client, investigation_id,
    )

    if not entities and not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found or has no data")

    report_format = ReportFormat(format)
    config = ReportConfig(
        title=f"Intelligence Report — {investigation_id}",
        investigation_id=investigation_id,
        format=report_format,
    )

    result = _generator.generate(config, entities, relationships, investigation)

    if report_format == ReportFormat.HTML:
        return HTMLResponse(content=result)
    elif report_format == ReportFormat.PDF:
        return Response(
            content=result,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=report-{investigation_id}.pdf"},
        )
    else:
        return result


@router.get("/{investigation_id}/preview")
async def preview_report(
    investigation_id: str,
    driver=Depends(get_neo4j),
) -> Any:
    """Preview a report as HTML."""
    client = Neo4jClient(driver)
    investigation, entities, relationships = await _fetch_investigation_data(
        client, investigation_id,
    )

    if not entities and not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found or has no data")

    config = ReportConfig(
        title=f"Intelligence Report — {investigation_id}",
        investigation_id=investigation_id,
        format=ReportFormat.HTML,
    )

    html = _generator.generate(config, entities, relationships, investigation)
    return HTMLResponse(content=html)
