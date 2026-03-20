"""Celery tasks for data collection jobs.

Pipeline: Collector → entity_factory → Neo4j → Redis pub/sub → WebSocket → Frontend
         → Auto-Pivot → child collection jobs
         → Alert Engine → persistent alerts
"""

import asyncio
import json

import structlog

from nexus.tasks import app

logger = structlog.get_logger()


def _run_async(coro):
    """Run an async coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


_COLLECTOR_MAP = {
    "CYBINT": ("nexus.collectors.cybint.manager", "CybintManager"),
    "SOCMINT": ("nexus.collectors.socmint.manager", "SocmintManager"),
    "SIGINT": ("nexus.collectors.sigint.manager", "SigintManager"),
    "GEOINT": ("nexus.collectors.geoint.manager", "GeointManager"),
}

# ---------------------------------------------------------------------------
# Auto-Pivot rules: entity_type → list of follow-up scans
# ---------------------------------------------------------------------------
_PIVOT_RULES: dict[str, list[dict[str, str]]] = {
    "IPAddress": [
        {"int_type": "CYBINT", "scan_type": "host"},
        {"int_type": "CYBINT", "scan_type": "ip"},
    ],
    "Domain": [
        {"int_type": "CYBINT", "scan_type": "certificates"},
        {"int_type": "CYBINT", "scan_type": "whois"},
        {"int_type": "CYBINT", "scan_type": "dns"},
    ],
    "SocialAccount": [
        {"int_type": "SOCMINT", "scan_type": "username_search"},
        {"int_type": "SOCMINT", "scan_type": "user_info"},
    ],
    "Person": [
        {"int_type": "SOCMINT", "scan_type": "username_search"},
    ],
    "Vulnerability": [
        {"int_type": "CYBINT", "scan_type": "search"},
    ],
}

MAX_PIVOT_DEPTH = 3
MAX_PIVOT_CHILDREN_PER_JOB = 10


async def get_pivot_suggestions(
    entity_id: str, entity_type: str, entity_name: str, conn,
) -> list[dict[str, str]]:
    """Suggest uncollected follow-up scans for an entity."""
    rules = _PIVOT_RULES.get(entity_type, [])
    if not rules:
        return []

    suggestions: list[dict[str, str]] = []
    for rule in rules:
        existing = await conn.fetchrow(
            """SELECT id FROM collection_jobs
               WHERE query = $1 AND int_type = $2 AND scan_type = $3
                     AND status = 'completed'
               LIMIT 1""",
            entity_name, rule["int_type"], rule["scan_type"],
        )
        if not existing:
            suggestions.append({
                "int_type": rule["int_type"],
                "scan_type": rule["scan_type"],
                "query": entity_name,
                "reason": f"No {rule['scan_type']} scan completed for this {entity_type}",
            })
    return suggestions


@app.task(bind=True, name="nexus.tasks.collection_tasks.run_collection")
def run_collection(
    self,
    job_id: str,
    int_type: str,
    query: str,
    scan_type: str,
    pivot_depth: int = 0,
    parent_job_id: str | None = None,
    auto_pivot: bool = False,
):
    """Execute a collection job: collect → persist to Neo4j → emit WebSocket events → auto-pivot."""
    logger.info(
        "collection_task.started",
        job_id=job_id, int_type=int_type, query=query,
        pivot_depth=pivot_depth, auto_pivot=auto_pivot,
    )

    async def _execute():
        import importlib

        import asyncpg
        import redis.asyncio as aioredis
        from neo4j import AsyncGraphDatabase

        from nexus.config import settings
        from nexus.knowledge.neo4j_client import Neo4jClient
        from nexus.knowledge.repository import EntityRepository
        from nexus.models.entity import RelationshipCreate, ExtractionMethod
        from nexus.processing.entity_factory import normalized_to_entities, infer_relationships
        from nexus.tasks.indexing_tasks import index_entities

        pool = await asyncpg.create_pool(dsn=settings.get_postgres_dsn(), min_size=1, max_size=2)
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

        async def _publish(event: str, data: dict):
            """Publish event to Redis for WebSocket bridge."""
            try:
                await redis_client.publish(
                    "nexus:ws:events",
                    json.dumps({"event": event, "data": data}),
                )
            except Exception:
                pass  # Non-critical: don't block pipeline on pub/sub failure

        try:
            client = Neo4jClient(neo4j_driver)
            repo = EntityRepository(client)

            # Mark running
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE collection_jobs SET status = 'running', progress = 5 WHERE id = $1",
                    job_id,
                )
            self.update_state(state="PROGRESS", meta={"progress": 5, "status": "running"})
            await _publish("collection:progress", {
                "jobId": job_id, "intType": int_type, "status": "running",
                "progress": 5, "query": query,
            })

            # ---------- Dispatch to collector ----------
            collector_entry = _COLLECTOR_MAP.get(int_type)
            if not collector_entry:
                raise ValueError(f"Unknown INT type: {int_type}")

            module_path, class_name = collector_entry
            mod = importlib.import_module(module_path)
            manager = getattr(mod, class_name)()
            results = await manager.collect(query=query, scan_type=scan_type) or []

            total_results = len(results)
            created_entity_ids: list[str] = []
            entity_name_to_id: dict[str, str] = {}
            all_created_entities = []  # Track EntityCreate objects for pivot

            # ---------- Process each result: create entities in Neo4j ----------
            try:
                for idx, result in enumerate(results):
                    progress = 10 + int((idx / max(total_results, 1)) * 80)

                    collector_name = result.metadata.get("collector", "unknown")
                    entity_creates = normalized_to_entities(
                        normalized=result.normalized,
                        source_int=result.source_int,
                        reliability_grade=result.reliability_grade,
                        collector_name=collector_name,
                    )
                    if not entity_creates:
                        continue

                    primary_entity = entity_creates[0]
                    secondary_entities = entity_creates[1:]

                    # Create primary entity in Neo4j
                    try:
                        primary_resp = await repo.create_entity(primary_entity)
                        created_entity_ids.append(primary_resp.id)
                        entity_name_to_id[primary_entity.name] = primary_resp.id
                        all_created_entities.append(primary_entity)

                        await _publish("entity:new", {
                            "id": primary_resp.id,
                            "type": primary_resp.type.value,
                            "name": primary_resp.name,
                            "confidence": primary_resp.confidence,
                            "sourceInt": primary_resp.source_int,
                            "riskScore": primary_resp.risk_score,
                            "jobId": job_id,
                        })

                        # Evaluate alert rules
                        try:
                            from nexus.services.alert_engine import AlertEngine
                            alert_engine = AlertEngine(pool, redis_client)
                            await alert_engine.evaluate_new_entity(
                                entity_id=primary_resp.id,
                                entity_name=primary_resp.name,
                                entity_type=primary_resp.type.value,
                                risk_score=primary_resp.risk_score,
                                source_int=primary_resp.source_int,
                                job_id=job_id,
                            )
                        except Exception:
                            pass  # Don't block pipeline on alert failure

                    except Exception as e:
                        logger.warning("collection.entity_create_failed",
                                       name=primary_entity.name, error=str(e))
                        continue

                    # Create secondary entities
                    for sec_entity in secondary_entities:
                        try:
                            sec_resp = await repo.create_entity(sec_entity)
                            created_entity_ids.append(sec_resp.id)
                            entity_name_to_id[sec_entity.name] = sec_resp.id
                            all_created_entities.append(sec_entity)
                            await _publish("entity:new", {
                                "id": sec_resp.id,
                                "type": sec_resp.type.value,
                                "name": sec_resp.name,
                                "confidence": sec_resp.confidence,
                                "sourceInt": sec_resp.source_int,
                                "riskScore": sec_resp.risk_score,
                                "jobId": job_id,
                            })
                        except Exception as e:
                            logger.warning("collection.secondary_entity_failed",
                                           name=sec_entity.name, error=str(e))

                    # Create inferred relationships
                    rel_specs = infer_relationships(
                        primary_entity.name, secondary_entities, result.source_int,
                    )
                    for rel_spec in rel_specs:
                        src_id = entity_name_to_id.get(rel_spec["source_name"])
                        tgt_id = entity_name_to_id.get(rel_spec["target_name"])
                        if src_id and tgt_id:
                            try:
                                await repo.create_relationship(RelationshipCreate(
                                    type=rel_spec["rel_type"],
                                    source_id=src_id,
                                    target_id=tgt_id,
                                    confidence=0.8,
                                    source_int=rel_spec["source_int"],
                                    method=ExtractionMethod.Pattern,
                                ))
                            except Exception:
                                pass  # Duplicate relationships are expected

                    # Periodic progress update
                    if idx % 5 == 0 or idx == total_results - 1:
                        async with pool.acquire() as conn:
                            await conn.execute(
                                "UPDATE collection_jobs SET progress = $2 WHERE id = $1",
                                job_id, progress,
                            )
                        self.update_state(state="PROGRESS", meta={"progress": progress})
                        await _publish("collection:progress", {
                            "jobId": job_id, "progress": progress,
                            "entitiesCreated": len(created_entity_ids),
                            "totalResults": total_results,
                        })

                # ---------- Auto-Pivot: dispatch follow-up collections ----------
                if auto_pivot and pivot_depth < MAX_PIVOT_DEPTH and all_created_entities:
                    pivot_count = 0
                    seen_pivots: set[tuple[str, str, str]] = set()

                    for entity_create in all_created_entities:
                        entity_type_str = entity_create.type.value
                        rules = _PIVOT_RULES.get(entity_type_str, [])

                        for rule in rules:
                            pivot_key = (rule["int_type"], rule["scan_type"], entity_create.name)
                            if pivot_key in seen_pivots:
                                continue
                            # Don't pivot back to the same query we just ran
                            if rule["int_type"] == int_type and rule["scan_type"] == scan_type and entity_create.name == query:
                                continue
                            seen_pivots.add(pivot_key)

                            if pivot_count >= MAX_PIVOT_CHILDREN_PER_JOB:
                                break

                            async with pool.acquire() as conn:
                                child_row = await conn.fetchrow(
                                    """INSERT INTO collection_jobs
                                       (int_type, query, scan_type, status, parent_job_id,
                                        pivot_depth, pivot_entity_type, auto_pivot)
                                       VALUES ($1, $2, $3, 'queued', $4, $5, $6, TRUE)
                                       RETURNING id""",
                                    rule["int_type"],
                                    entity_create.name,
                                    rule["scan_type"],
                                    job_id,
                                    pivot_depth + 1,
                                    entity_type_str,
                                )

                            run_collection.delay(
                                str(child_row["id"]),
                                rule["int_type"],
                                entity_create.name,
                                rule["scan_type"],
                                pivot_depth=pivot_depth + 1,
                                parent_job_id=job_id,
                                auto_pivot=True,
                            )
                            pivot_count += 1

                            await _publish("pivot:dispatched", {
                                "parentJobId": job_id,
                                "childJobId": str(child_row["id"]),
                                "entityType": entity_type_str,
                                "entityName": entity_create.name,
                                "scanType": rule["scan_type"],
                                "intType": rule["int_type"],
                                "pivotDepth": pivot_depth + 1,
                            })

                    if pivot_count:
                        logger.info("collection.pivot_dispatched",
                                    job_id=job_id, pivot_count=pivot_count,
                                    depth=pivot_depth + 1)

                # Auto community detection after significant collection
                if len(created_entity_ids) >= 5:
                    try:
                        from nexus.knowledge.graph_algorithms import GraphAlgorithms
                        algo = GraphAlgorithms(client)
                        communities = await algo.run_louvain()
                        for comm in (communities or []):
                            for member in comm.get("members", []):
                                member_id = member.get("id") if isinstance(member, dict) else str(member)
                                if member_id:
                                    await client.execute_write(
                                        "MATCH (e:Entity {id: $id}) SET e.communityId = $cid",
                                        {"id": member_id, "cid": comm.get("community_id", 0)},
                                    )
                        await _publish("community:updated", {
                            "communities": len(communities or []),
                            "jobId": job_id,
                        })
                        logger.info("collection.community_detection_done",
                                    communities=len(communities or []))
                    except Exception as exc:
                        logger.debug("collection.community_detection_skipped", error=str(exc))

                # Dispatch indexing in batches
                if created_entity_ids:
                    for i in range(0, len(created_entity_ids), 100):
                        batch = created_entity_ids[i:i + 100]
                        index_entities.delay(batch)

                # Mark completed + store entity_ids
                result_count = len(created_entity_ids)
                async with pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE collection_jobs
                           SET status = 'completed', progress = 100,
                               result_count = $2, completed_at = NOW(),
                               entity_ids = $3
                           WHERE id = $1""",
                        job_id, result_count, created_entity_ids,
                    )
                self.update_state(state="SUCCESS", meta={
                    "progress": 100, "result_count": result_count,
                })
                await _publish("collection:completed", {
                    "jobId": job_id, "intType": int_type, "query": query,
                    "resultCount": result_count,
                    "entityIds": created_entity_ids[:50],
                })
                logger.info("collection_task.completed",
                            job_id=job_id, result_count=result_count)

            except Exception as e:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE collection_jobs
                           SET status = 'failed', error = $2, completed_at = NOW()
                           WHERE id = $1""",
                        job_id, str(e)[:500],
                    )
                await _publish("collection:failed", {
                    "jobId": job_id, "error": str(e)[:200],
                })
                logger.error("collection_task.failed", job_id=job_id, error=str(e))
                raise

        finally:
            await pool.close()
            await neo4j_driver.close()
            await redis_client.close()

    _run_async(_execute())
    return {"job_id": job_id, "status": "completed"}
