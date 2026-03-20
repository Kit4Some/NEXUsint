"""Collection control routes — trigger and monitor data collection jobs."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from nexus.dependencies import get_pg_connection, get_neo4j
from nexus.models.collection import (
    CollectionRequest,
    CollectionJobResponse,
    CollectionStatus,
    IntType,
)

router = APIRouter()


def _row_to_response(row) -> CollectionJobResponse:
    """Convert a DB row to CollectionJobResponse."""
    return CollectionJobResponse(
        id=str(row["id"]),
        int_type=IntType(row["int_type"]),
        query=row["query"],
        scan_type=row["scan_type"],
        status=CollectionStatus(row["status"]),
        progress=row["progress"],
        result_count=row["result_count"],
        error=row["error"],
        parent_job_id=str(row["parent_job_id"]) if row.get("parent_job_id") else None,
        pivot_depth=row.get("pivot_depth", 0),
        pivot_entity_type=row.get("pivot_entity_type"),
        auto_pivot=row.get("auto_pivot", False),
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


async def _create_job(
    int_type: IntType,
    request: CollectionRequest,
    conn,
) -> CollectionJobResponse:
    """Create a collection job record and dispatch to worker."""
    row = await conn.fetchrow(
        """
        INSERT INTO collection_jobs (int_type, query, scan_type, status, auto_pivot)
        VALUES ($1, $2, $3, 'queued', $4)
        RETURNING *
        """,
        int_type.value,
        request.query,
        request.scan_type,
        request.auto_pivot,
    )

    from nexus.tasks.collection_tasks import run_collection
    run_collection.delay(
        str(row["id"]), int_type.value, request.query, request.scan_type,
        pivot_depth=0, parent_job_id=None, auto_pivot=request.auto_pivot,
    )

    return _row_to_response(row)


@router.post("/cybint", response_model=CollectionJobResponse, status_code=201)
async def collect_cybint(
    request: CollectionRequest,
    conn=Depends(get_pg_connection),
):
    """Start a CYBINT collection job (Shodan, DNS, CT logs, threat intel)."""
    return await _create_job(IntType.CYBINT, request, conn)


@router.post("/socmint", response_model=CollectionJobResponse, status_code=201)
async def collect_socmint(
    request: CollectionRequest,
    conn=Depends(get_pg_connection),
):
    """Start a SOCMINT collection job."""
    return await _create_job(IntType.SOCMINT, request, conn)


@router.post("/geoint", response_model=CollectionJobResponse, status_code=201)
async def collect_geoint(
    request: CollectionRequest,
    conn=Depends(get_pg_connection),
):
    """Start a GEOINT collection job."""
    return await _create_job(IntType.GEOINT, request, conn)


@router.post("/sigint", response_model=CollectionJobResponse, status_code=201)
async def collect_sigint(
    request: CollectionRequest,
    conn=Depends(get_pg_connection),
):
    """Start a SIGINT collection job."""
    return await _create_job(IntType.SIGINT, request, conn)


@router.get("/status/{job_id}", response_model=CollectionJobResponse)
async def get_collection_status(
    job_id: str,
    conn=Depends(get_pg_connection),
):
    """Get the status of a collection job."""
    row = await conn.fetchrow("SELECT * FROM collection_jobs WHERE id = $1", job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Collection job not found")
    return _row_to_response(row)


@router.get("/tree/{job_id}")
async def get_pivot_tree(
    job_id: str,
    conn=Depends(get_pg_connection),
) -> list[dict[str, Any]]:
    """Get the full pivot tree for a collection job (recursive)."""
    rows = await conn.fetch(
        """
        WITH RECURSIVE tree AS (
            SELECT id, int_type, query, scan_type, status, progress, result_count,
                   parent_job_id, pivot_depth, pivot_entity_type, auto_pivot, created_at, completed_at
            FROM collection_jobs WHERE id = $1
            UNION ALL
            SELECT cj.id, cj.int_type, cj.query, cj.scan_type, cj.status, cj.progress,
                   cj.result_count, cj.parent_job_id, cj.pivot_depth, cj.pivot_entity_type,
                   cj.auto_pivot, cj.created_at, cj.completed_at
            FROM collection_jobs cj
            INNER JOIN tree t ON cj.parent_job_id = t.id
        )
        SELECT * FROM tree ORDER BY pivot_depth, created_at
        """,
        job_id,
    )
    return [
        {
            "id": str(r["id"]),
            "int_type": r["int_type"],
            "query": r["query"],
            "scan_type": r["scan_type"],
            "status": r["status"],
            "progress": r["progress"],
            "result_count": r["result_count"],
            "parent_job_id": str(r["parent_job_id"]) if r["parent_job_id"] else None,
            "pivot_depth": r["pivot_depth"],
            "pivot_entity_type": r["pivot_entity_type"],
            "auto_pivot": r["auto_pivot"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
        }
        for r in rows
    ]


@router.get("/history")
async def get_collection_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    int_type: str | None = Query(None),
    status: str | None = Query(None),
    conn=Depends(get_pg_connection),
) -> dict[str, Any]:
    """Return paginated collection job history."""
    conditions: list[str] = []
    params: list[Any] = []
    idx = 1

    if int_type:
        conditions.append(f"int_type = ${idx}")
        params.append(int_type)
        idx += 1
    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    count_params = list(params)
    total = await conn.fetchval(
        f"SELECT COUNT(*) FROM collection_jobs {where}", *count_params,
    )

    params.extend([limit, offset])
    rows = await conn.fetch(
        f"""SELECT id, int_type, query, scan_type, status, progress,
                   result_count, error, parent_job_id, pivot_depth,
                   auto_pivot, created_at, completed_at
            FROM collection_jobs {where}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}""",
        *params,
    )

    jobs = [
        {
            "id": str(r["id"]),
            "int_type": r["int_type"],
            "query": r["query"],
            "scan_type": r["scan_type"],
            "status": r["status"],
            "progress": r["progress"],
            "result_count": r["result_count"],
            "error": r["error"],
            "parent_job_id": str(r["parent_job_id"]) if r["parent_job_id"] else None,
            "pivot_depth": r["pivot_depth"],
            "auto_pivot": r["auto_pivot"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
        }
        for r in rows
    ]
    return {"jobs": jobs, "total": total, "limit": limit, "offset": offset}


@router.get("/jobs/{job_id}/entities")
async def get_job_entities(
    job_id: str,
    conn=Depends(get_pg_connection),
    neo4j=Depends(get_neo4j),
) -> list[dict[str, Any]]:
    """Return entities created by a specific collection job."""
    from nexus.knowledge.neo4j_client import Neo4jClient

    row = await conn.fetchrow(
        "SELECT entity_ids FROM collection_jobs WHERE id = $1", job_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Collection job not found")

    entity_ids = row["entity_ids"] or []
    if not entity_ids:
        return []

    client = Neo4jClient(neo4j)
    records = await client.execute_read(
        """MATCH (e:Entity) WHERE e.id IN $ids
           RETURN e.id AS id, e.name AS name, e.type AS type,
                  e.confidence AS confidence, e.sourceInt AS sourceInt,
                  e.riskScore AS riskScore""",
        {"ids": entity_ids},
    )
    return [dict(r) for r in records]
