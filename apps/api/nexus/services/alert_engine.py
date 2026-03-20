"""Alert evaluation engine — checks rules against new/changed entities."""

import json

import structlog
import asyncpg
import redis.asyncio as aioredis

logger = structlog.get_logger()


class AlertEngine:
    """Evaluates alert rules and persists triggered alerts."""

    def __init__(self, pool: asyncpg.Pool, redis_client: aioredis.Redis) -> None:
        self._pool = pool
        self._redis = redis_client

    async def evaluate_new_entity(
        self,
        entity_id: str,
        entity_name: str,
        entity_type: str,
        risk_score: float,
        source_int: str,
        job_id: str | None = None,
    ) -> list[dict]:
        """Evaluate alert rules against a newly created entity. Returns generated alerts."""
        alerts: list[dict] = []

        async with self._pool.acquire() as conn:
            rules = await conn.fetch(
                "SELECT * FROM alert_rules WHERE active = TRUE"
            )

            for rule in rules:
                conditions = rule["conditions"]
                if isinstance(conditions, str):
                    conditions = json.loads(conditions)

                triggered = False
                title = ""
                description = ""

                if rule["rule_type"] == "new_entity":
                    target_types = conditions.get("entity_types", [])
                    if not target_types or entity_type in target_types:
                        triggered = True
                        title = f"New {entity_type} detected: {entity_name}"
                        description = (
                            f"A new {entity_type} entity was discovered "
                            f"via {source_int} collection."
                        )

                elif rule["rule_type"] == "high_risk":
                    threshold = conditions.get("min_risk_score", 7.0)
                    if risk_score >= threshold:
                        triggered = True
                        title = f"High-risk entity: {entity_name} (score: {risk_score}/10)"
                        description = (
                            f"{entity_type} entity has risk score {risk_score}/10, "
                            f"exceeding threshold {threshold}."
                        )

                if not triggered:
                    continue

                alert_row = await conn.fetchrow(
                    """INSERT INTO alerts
                       (entity_id, entity_name, alert_type, severity,
                        title, description, metadata, source_job_id)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                       RETURNING *""",
                    entity_id, entity_name, rule["rule_type"], rule["severity"],
                    title, description,
                    json.dumps({"rule_id": str(rule["id"]), "conditions": conditions}),
                    job_id,
                )

                alert_data = {
                    "id": str(alert_row["id"]),
                    "entityId": entity_id,
                    "entityName": entity_name,
                    "alertType": rule["rule_type"],
                    "severity": rule["severity"],
                    "title": title,
                    "description": description,
                    "createdAt": alert_row["created_at"].isoformat(),
                }
                alerts.append(alert_data)

                # Publish to WebSocket via Redis
                try:
                    await self._redis.publish(
                        "nexus:ws:events",
                        json.dumps({"event": "alert:received", "data": alert_data}),
                    )
                except Exception:
                    pass  # Non-critical

                logger.info("alert.triggered",
                            alert_type=rule["rule_type"],
                            entity_name=entity_name,
                            severity=rule["severity"])

        return alerts
