"""Monitoring routes — watch list management and alert CRUD."""

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from nexus.dependencies import get_pg_connection, get_redis
from nexus.api.middleware.rbac import require_analyst
from nexus.models.monitoring import (
    WatchTargetCreate,
    WatchTargetResponse,
    WatchTargetUpdate,
    AlertResponse,
    AlertRuleCreate,
    AlertRuleResponse,
)

logger = structlog.get_logger()
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _watch_row_to_response(row) -> WatchTargetResponse:
    return WatchTargetResponse(
        id=str(row["id"]),
        entity_id=row["entity_id"],
        entity_name=row["entity_name"],
        entity_type=row["entity_type"],
        int_type=row["int_type"],
        scan_type=row["scan_type"],
        query=row["query"],
        interval_hours=row["interval_hours"],
        auto_pivot=row["auto_pivot"],
        last_collected_at=row["last_collected_at"],
        next_collection_at=row["next_collection_at"],
        active=row["active"],
        created_at=row["created_at"],
    )


def _alert_row_to_response(row) -> AlertResponse:
    metadata = row["metadata"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return AlertResponse(
        id=str(row["id"]),
        entity_id=row["entity_id"],
        entity_name=row["entity_name"],
        alert_type=row["alert_type"],
        severity=row["severity"],
        title=row["title"],
        description=row["description"],
        metadata=metadata or {},
        acknowledged=row["acknowledged"],
        created_at=row["created_at"],
    )


def _rule_row_to_response(row) -> AlertRuleResponse:
    conditions = row["conditions"]
    if isinstance(conditions, str):
        conditions = json.loads(conditions)
    return AlertRuleResponse(
        id=str(row["id"]),
        name=row["name"],
        rule_type=row["rule_type"],
        conditions=conditions or {},
        severity=row["severity"],
        active=row["active"],
        created_at=row["created_at"],
    )


# ---------------------------------------------------------------------------
# Watch Targets
# ---------------------------------------------------------------------------

@router.post("/targets", response_model=WatchTargetResponse, status_code=201)
async def create_watch_target(
    target: WatchTargetCreate,
    _user=Depends(require_analyst),
    conn=Depends(get_pg_connection),
):
    """Add an entity to the monitoring watch list."""
    row = await conn.fetchrow(
        """INSERT INTO watch_targets
           (entity_id, entity_name, entity_type, int_type, scan_type, query,
            interval_hours, auto_pivot)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
           RETURNING *""",
        target.entity_id, target.entity_name, target.entity_type,
        target.int_type, target.scan_type, target.query,
        target.interval_hours, target.auto_pivot,
    )
    logger.info("monitoring.watch_target_created",
                entity_name=target.entity_name, interval=target.interval_hours)
    return _watch_row_to_response(row)


@router.get("/targets", response_model=list[WatchTargetResponse])
async def list_watch_targets(
    active_only: bool = Query(True),
    conn=Depends(get_pg_connection),
):
    """List all watch targets."""
    if active_only:
        rows = await conn.fetch(
            "SELECT * FROM watch_targets WHERE active = TRUE ORDER BY next_collection_at ASC"
        )
    else:
        rows = await conn.fetch("SELECT * FROM watch_targets ORDER BY created_at DESC")
    return [_watch_row_to_response(r) for r in rows]


@router.patch("/targets/{target_id}", response_model=WatchTargetResponse)
async def update_watch_target(
    target_id: str,
    updates: WatchTargetUpdate,
    _user=Depends(require_analyst),
    conn=Depends(get_pg_connection),
):
    """Update watch target settings."""
    sets: list[str] = []
    params: list[Any] = []
    idx = 1
    if updates.interval_hours is not None:
        sets.append(f"interval_hours = ${idx}")
        params.append(updates.interval_hours)
        idx += 1
    if updates.active is not None:
        sets.append(f"active = ${idx}")
        params.append(updates.active)
        idx += 1
    if updates.auto_pivot is not None:
        sets.append(f"auto_pivot = ${idx}")
        params.append(updates.auto_pivot)
        idx += 1

    if not sets:
        raise HTTPException(status_code=400, detail="No updates provided")

    sets.append("updated_at = NOW()")
    params.append(target_id)

    row = await conn.fetchrow(
        f"UPDATE watch_targets SET {', '.join(sets)} WHERE id = ${idx} RETURNING *",
        *params,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Watch target not found")
    return _watch_row_to_response(row)


@router.delete("/targets/{target_id}", status_code=204)
async def delete_watch_target(
    target_id: str,
    _user=Depends(require_analyst),
    conn=Depends(get_pg_connection),
):
    """Remove a watch target."""
    result = await conn.execute("DELETE FROM watch_targets WHERE id = $1", target_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Watch target not found")


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    unacknowledged_only: bool = Query(False),
    severity: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    conn=Depends(get_pg_connection),
):
    """List alerts with optional filtering."""
    conditions: list[str] = []
    params: list[Any] = []
    idx = 1

    if unacknowledged_only:
        conditions.append("acknowledged = FALSE")
    if severity:
        conditions.append(f"severity = ${idx}")
        params.append(severity)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])

    rows = await conn.fetch(
        f"SELECT * FROM alerts {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
        *params,
    )
    return [_alert_row_to_response(r) for r in rows]


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    _user=Depends(require_analyst),
    conn=Depends(get_pg_connection),
):
    """Mark an alert as acknowledged."""
    row = await conn.fetchrow(
        """UPDATE alerts SET acknowledged = TRUE, acknowledged_at = NOW()
           WHERE id = $1 RETURNING id""",
        alert_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"detail": "Alert acknowledged"}


# ---------------------------------------------------------------------------
# Alert Rules
# ---------------------------------------------------------------------------

@router.post("/alerts/rules", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    rule: AlertRuleCreate,
    _user=Depends(require_analyst),
    conn=Depends(get_pg_connection),
):
    """Create a new alert rule."""
    row = await conn.fetchrow(
        """INSERT INTO alert_rules (name, rule_type, conditions, severity)
           VALUES ($1, $2, $3, $4) RETURNING *""",
        rule.name, rule.rule_type, json.dumps(rule.conditions), rule.severity,
    )
    return _rule_row_to_response(row)


@router.get("/alerts/rules", response_model=list[AlertRuleResponse])
async def list_alert_rules(conn=Depends(get_pg_connection)):
    """List all alert rules."""
    rows = await conn.fetch("SELECT * FROM alert_rules ORDER BY created_at DESC")
    return [_rule_row_to_response(r) for r in rows]


@router.delete("/alerts/rules/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: str,
    _user=Depends(require_analyst),
    conn=Depends(get_pg_connection),
):
    """Delete an alert rule."""
    result = await conn.execute("DELETE FROM alert_rules WHERE id = $1", rule_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Alert rule not found")


# ---------------------------------------------------------------------------
# Live Feed Control (SIGINT real-time ADS-B)
# ---------------------------------------------------------------------------

class LiveFeedBBox(BaseModel):
    """Bounding box for live ADS-B area scan."""
    lamin: float
    lomin: float
    lamax: float
    lomax: float


@router.post("/live-feed/start")
async def start_live_feed(
    bbox: LiveFeedBBox,
    _user=Depends(require_analyst),
    redis=Depends(get_redis),
):
    """Activate the SIGINT live feed with the given bounding box."""
    await redis.set("nexus:sigint:live_bbox", json.dumps(bbox.model_dump()))
    await redis.set("nexus:sigint:live_active", "1")
    logger.info("monitoring.live_feed.started", bbox=bbox.model_dump())
    return {"status": "active", "bbox": bbox.model_dump()}


@router.post("/live-feed/stop")
async def stop_live_feed(
    _user=Depends(require_analyst),
    redis=Depends(get_redis),
):
    """Deactivate the SIGINT live feed."""
    await redis.delete("nexus:sigint:live_active")
    logger.info("monitoring.live_feed.stopped")
    return {"status": "stopped"}


@router.get("/live-feed/status")
async def get_live_feed_status(redis=Depends(get_redis)):
    """Return current live feed status, bbox, and last scan metadata."""
    active = await redis.get("nexus:sigint:live_active")
    bbox_raw = await redis.get("nexus:sigint:live_bbox")
    last_scan_raw = await redis.get("nexus:sigint:live_last_scan")

    return {
        "active": active == "1",
        "bbox": json.loads(bbox_raw) if bbox_raw else None,
        "last_scan": json.loads(last_scan_raw) if last_scan_raw else None,
    }
