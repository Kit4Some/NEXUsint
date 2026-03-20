"""Investigation management routes."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from nexus.dependencies import get_pg_connection
from nexus.api.middleware.rbac import require_analyst, require_viewer
from nexus.models.investigation import (
    InvestigationCreate,
    InvestigationResponse,
    InvestigationStatus,
    IntelligenceReportResponse,
)

router = APIRouter()


@router.post("", response_model=InvestigationResponse, status_code=201)
async def create_investigation(
    data: InvestigationCreate,
    _user=Depends(require_analyst),
    conn=Depends(get_pg_connection),
):
    """Create a new investigation."""
    row = await conn.fetchrow(
        """
        INSERT INTO investigations (query, target_ints, priority, status)
        VALUES ($1, $2, $3, 'created')
        RETURNING *
        """,
        data.query,
        data.target_ints,
        data.priority.value,
    )

    return InvestigationResponse(
        id=str(row["id"]),
        query=row["query"],
        target_ints=row["target_ints"],
        status=InvestigationStatus(row["status"]),
        priority=row["priority"],
        progress=row["progress"],
        entity_count=row["entity_count"],
        relationship_count=row["relationship_count"],
        report=row["report"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: str,
    _user=Depends(require_viewer),
    conn=Depends(get_pg_connection),
):
    """Get investigation details."""
    row = await conn.fetchrow(
        "SELECT * FROM investigations WHERE id = $1", investigation_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return InvestigationResponse(
        id=str(row["id"]),
        query=row["query"],
        target_ints=row["target_ints"],
        status=InvestigationStatus(row["status"]),
        priority=row["priority"],
        progress=row["progress"],
        entity_count=row["entity_count"],
        relationship_count=row["relationship_count"],
        report=row["report"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/{investigation_id}/execute", response_model=InvestigationResponse)
async def execute_investigation(
    investigation_id: str,
    _user=Depends(require_analyst),
    conn=Depends(get_pg_connection),
):
    """Execute the multi-agent pipeline for an investigation.

    In Phase 1, this updates the status. LangGraph agent integration comes in Phase 2.
    """
    row = await conn.fetchrow(
        """
        UPDATE investigations SET status = 'collecting', progress = 10, updated_at = NOW()
        WHERE id = $1 AND status = 'created'
        RETURNING *
        """,
        investigation_id,
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found or already executing",
        )

    # Dispatch LangGraph multi-agent pipeline in background
    import asyncio
    from nexus.agents.orchestrator import run_investigation

    async def _run_pipeline(inv_id: str, inv_query: str, inv_ints: list, inv_priority: str):
        try:
            final_state = await run_investigation(
                query=inv_query,
                target_ints=inv_ints,
                investigation_id=inv_id,
                priority=inv_priority,
            )
            import json as _json
            from nexus.dependencies import lifespan_state

            pool = lifespan_state.pg_pool
            if pool:
                async with pool.acquire() as update_conn:
                    await update_conn.execute(
                        """
                        UPDATE investigations
                        SET status = $2, progress = $3,
                            entity_count = $4, relationship_count = $5,
                            report = $6::jsonb, updated_at = NOW()
                        WHERE id = $1
                        """,
                        inv_id,
                        final_state.get("status", "completed"),
                        final_state.get("progress", 100),
                        len(final_state.get("verified_entities", [])),
                        len(final_state.get("extracted_relationships", [])),
                        _json.dumps({
                            "title": f"Investigation: {inv_query}",
                            "summary": final_state.get("report", "")[:500],
                            "body": final_state.get("report", ""),
                            "entities": final_state.get("verified_entities", [])[:100],
                            "relationships": final_state.get("extracted_relationships", [])[:100],
                            "confidence_overall": 0.0,
                            "verification_status": "auto_verified",
                            "verification_notes": final_state.get("verification_notes", []),
                        }),
                    )
        except Exception as e:
            from nexus.dependencies import lifespan_state
            pool = lifespan_state.pg_pool
            if pool:
                async with pool.acquire() as update_conn:
                    await update_conn.execute(
                        "UPDATE investigations SET status = 'failed', updated_at = NOW() WHERE id = $1",
                        inv_id,
                    )

    asyncio.create_task(_run_pipeline(
        str(row["id"]), row["query"], row["target_ints"], row["priority"],
    ))

    return InvestigationResponse(
        id=str(row["id"]),
        query=row["query"],
        target_ints=row["target_ints"],
        status=InvestigationStatus(row["status"]),
        priority=row["priority"],
        progress=row["progress"],
        entity_count=row["entity_count"],
        relationship_count=row["relationship_count"],
        report=row["report"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{investigation_id}/status", response_model=InvestigationResponse)
async def get_investigation_status(
    investigation_id: str,
    conn=Depends(get_pg_connection),
):
    """Get the execution status of an investigation."""
    row = await conn.fetchrow(
        "SELECT * FROM investigations WHERE id = $1", investigation_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return InvestigationResponse(
        id=str(row["id"]),
        query=row["query"],
        target_ints=row["target_ints"],
        status=InvestigationStatus(row["status"]),
        priority=row["priority"],
        progress=row["progress"],
        entity_count=row["entity_count"],
        relationship_count=row["relationship_count"],
        report=row["report"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{investigation_id}/report", response_model=IntelligenceReportResponse)
async def get_investigation_report(
    investigation_id: str,
    conn=Depends(get_pg_connection),
):
    """Get the intelligence report for a completed investigation."""
    row = await conn.fetchrow(
        "SELECT * FROM investigations WHERE id = $1 AND status = 'completed'",
        investigation_id,
    )
    if not row or not row["report"]:
        raise HTTPException(status_code=404, detail="Report not available")

    report = row["report"]
    return IntelligenceReportResponse(
        id=report.get("id", str(uuid4())),
        investigation_id=str(row["id"]),
        title=report.get("title", ""),
        summary=report.get("summary", ""),
        body=report.get("body", ""),
        entities=report.get("entities", []),
        relationships=report.get("relationships", []),
        confidence_overall=report.get("confidence_overall", 0.0),
        verification_status=report.get("verification_status", "needs_review"),
        verification_notes=report.get("verification_notes", []),
        generated_at=row["updated_at"],
    )
