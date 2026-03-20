"""Dashboard aggregation endpoints."""

from fastapi import APIRouter, Depends, Query

from nexus.dependencies import get_neo4j, get_pg_pool
from nexus.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/stats")
async def dashboard_stats(
    current_user=Depends(get_current_user),
    driver=Depends(get_neo4j),
    pool=Depends(get_pg_pool),
):
    """Aggregated dashboard metrics."""

    # Threat level from top entity risk scores
    async with driver.session() as session:
        risk_result = await session.run(
            "MATCH (e:Entity) WHERE e.riskScore IS NOT NULL "
            "RETURN avg(e.riskScore) AS avg_risk, max(e.riskScore) AS max_risk, "
            "count(e) AS total_entities"
        )
        risk_data = await risk_result.single()

    avg_risk = risk_data["avg_risk"] or 0 if risk_data else 0
    max_risk = risk_data["max_risk"] or 0 if risk_data else 0
    total_entities = risk_data["total_entities"] or 0 if risk_data else 0

    threat_score = min(round(avg_risk * 10), 100)
    if max_risk >= 9:
        threat_level = "CRITICAL"
    elif max_risk >= 7:
        threat_level = "HIGH"
    elif avg_risk >= 4:
        threat_level = "MEDIUM"
    else:
        threat_level = "LOW"

    # INT coverage — entity count per source intelligence type
    async with driver.session() as session:
        int_result = await session.run(
            "MATCH (e:Entity) WHERE e.sourceInt IS NOT NULL "
            "RETURN e.sourceInt AS source_int, count(e) AS count "
            "ORDER BY count DESC"
        )
        int_records = await int_result.data()

    int_coverage = {r["source_int"]: r["count"] for r in int_records}

    # Active collection jobs from PostgreSQL
    active_collections = []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, int_type, query, scan_type, progress, status "
            "FROM collection_jobs WHERE status IN ('running', 'queued') "
            "ORDER BY created_at DESC LIMIT 20"
        )
        for row in rows:
            active_collections.append({
                "id": str(row["id"]),
                "int_type": row["int_type"],
                "query": row["query"],
                "scan_type": row["scan_type"],
                "progress": row["progress"],
                "status": row["status"],
            })

    # Confidence distribution histogram
    async with driver.session() as session:
        conf_result = await session.run(
            "MATCH (e:Entity) WHERE e.confidence IS NOT NULL "
            "RETURN "
            "  sum(CASE WHEN e.confidence < 0.2 THEN 1 ELSE 0 END) AS b1, "
            "  sum(CASE WHEN e.confidence >= 0.2 AND e.confidence < 0.4 THEN 1 ELSE 0 END) AS b2, "
            "  sum(CASE WHEN e.confidence >= 0.4 AND e.confidence < 0.6 THEN 1 ELSE 0 END) AS b3, "
            "  sum(CASE WHEN e.confidence >= 0.6 AND e.confidence < 0.8 THEN 1 ELSE 0 END) AS b4, "
            "  sum(CASE WHEN e.confidence >= 0.8 THEN 1 ELSE 0 END) AS b5"
        )
        conf_data = await conf_result.single()

    confidence_distribution = [
        {"bucket": "0-0.2", "count": conf_data["b1"] or 0},
        {"bucket": "0.2-0.4", "count": conf_data["b2"] or 0},
        {"bucket": "0.4-0.6", "count": conf_data["b3"] or 0},
        {"bucket": "0.6-0.8", "count": conf_data["b4"] or 0},
        {"bucket": "0.8-1.0", "count": conf_data["b5"] or 0},
    ] if conf_data else []

    return {
        "threat_level": threat_level,
        "threat_score": threat_score,
        "total_entities": total_entities,
        "int_coverage": int_coverage,
        "active_collections": active_collections,
        "confidence_distribution": confidence_distribution,
    }


@router.get("/recent-investigations")
async def recent_investigations(
    status: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    current_user=Depends(get_current_user),
    pool=Depends(get_pg_pool),
):
    """Paginated investigation history with optional status filter."""
    async with pool.acquire() as conn:
        where = "WHERE 1=1"
        params: list = []
        idx = 1

        if status:
            where += f" AND status = ${idx}"
            params.append(status)
            idx += 1

        count_row = await conn.fetchrow(
            f"SELECT count(*) AS total FROM investigations {where}", *params
        )
        total = count_row["total"] if count_row else 0

        params.extend([limit, offset])
        rows = await conn.fetch(
            f"SELECT id, query, status, priority, entity_count, created_at, updated_at "
            f"FROM investigations {where} "
            f"ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
            *params,
        )

    items = [
        {
            "id": str(row["id"]),
            "query": row["query"],
            "status": row["status"],
            "priority": row["priority"],
            "entity_count": row["entity_count"] or 0,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]

    return {"total": total, "items": items}
