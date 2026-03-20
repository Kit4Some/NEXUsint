"""Celery Beat tasks for persistent monitoring and watch list execution."""

import asyncio
import json
from datetime import datetime, timezone

import structlog

from nexus.tasks import app

logger = structlog.get_logger()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="nexus.tasks.monitoring_tasks.check_watch_targets")
def check_watch_targets():
    """Check for overdue watch targets and dispatch collection jobs."""
    logger.info("monitoring.check_watch_targets.started")

    async def _execute():
        import asyncpg

        from nexus.config import settings
        from nexus.tasks.collection_tasks import run_collection

        pool = await asyncpg.create_pool(dsn=settings.get_postgres_dsn(), min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                overdue = await conn.fetch(
                    """SELECT * FROM watch_targets
                       WHERE active = TRUE AND next_collection_at <= NOW()
                       ORDER BY next_collection_at ASC
                       LIMIT 20"""
                )

                dispatched = 0
                for target in overdue:
                    row = await conn.fetchrow(
                        """INSERT INTO collection_jobs
                           (int_type, query, scan_type, status, auto_pivot)
                           VALUES ($1, $2, $3, 'queued', $4)
                           RETURNING id""",
                        target["int_type"],
                        target["query"],
                        target["scan_type"],
                        target["auto_pivot"],
                    )

                    run_collection.delay(
                        str(row["id"]),
                        target["int_type"],
                        target["query"],
                        target["scan_type"],
                        pivot_depth=0,
                        parent_job_id=None,
                        auto_pivot=target["auto_pivot"],
                    )

                    await conn.execute(
                        """UPDATE watch_targets
                           SET last_collected_at = NOW(),
                               next_collection_at = NOW() + ($2 || ' hours')::INTERVAL,
                               updated_at = NOW()
                           WHERE id = $1""",
                        target["id"],
                        str(target["interval_hours"]),
                    )
                    dispatched += 1

                logger.info("monitoring.check_watch_targets.done",
                            overdue_count=len(overdue), dispatched=dispatched)
        finally:
            await pool.close()

    _run_async(_execute())


@app.task(name="nexus.tasks.monitoring_tasks.sigint_area_scan")
def sigint_area_scan():
    """Periodic ADS-B area scan — fetch aircraft positions and push to map via WebSocket.

    Reads the active scan bbox from Redis (``nexus:sigint:live_bbox``).
    If no bbox is configured or the feed is not active, the task is a no-op.
    """
    logger.info("sigint.area_scan.started")

    async def _execute():
        import redis.asyncio as aioredis

        from nexus.config import settings

        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            # Check if live feed is active
            active = await redis_client.get("nexus:sigint:live_active")
            if active != "1":
                logger.debug("sigint.area_scan.skipped", reason="feed_inactive")
                return

            bbox_raw = await redis_client.get("nexus:sigint:live_bbox")
            if not bbox_raw:
                logger.debug("sigint.area_scan.skipped", reason="no_bbox")
                return

            bbox = json.loads(bbox_raw)

            # Collect aircraft via OpenSky
            from nexus.collectors.sigint.adsb_collector import ADSBCollector
            from nexus.collectors.base import CollectionQuery

            collector = ADSBCollector()
            results = await collector.collect(CollectionQuery(
                query="area_scan",
                scan_type="area_aircraft",
                options=bbox,
            ))

            if not results:
                await redis_client.set("nexus:sigint:live_last_scan", json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "aircraft_count": 0,
                }))
                return

            # Connect to Neo4j for entity upsert
            from neo4j import AsyncGraphDatabase
            from nexus.knowledge.neo4j_client import Neo4jClient

            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            client = Neo4jClient(driver)

            tracks = []
            new_count = 0

            try:
                for r in results:
                    n = r.normalized
                    icao24 = n.get("icao24", "")
                    if not icao24:
                        continue

                    entity_id = f"aircraft-{icao24}"
                    lat = n.get("latitude")
                    lng = n.get("longitude")
                    if lat is None or lng is None:
                        continue

                    callsign = n.get("callsign", icao24)
                    heading = n.get("heading") or 0
                    velocity = n.get("velocity") or 0
                    altitude = n.get("baro_altitude") or 0
                    country = n.get("origin_country", "")

                    # Upsert Aircraft entity in Neo4j
                    existing = await client.execute_read(
                        "MATCH (e:Entity {id: $id}) RETURN e.id AS id LIMIT 1",
                        {"id": entity_id},
                    )

                    if not existing:
                        await client.execute_write(
                            """CREATE (e:Entity {
                                id: $id, name: $name, type: 'Aircraft',
                                confidence: 0.85, sourceInt: 'SIGINT',
                                riskScore: 1.0,
                                coordinates: point({latitude: $lat, longitude: $lng}),
                                latitude: $lat, longitude: $lng,
                                properties: $props,
                                createdAt: datetime(), updatedAt: datetime()
                            })""",
                            {
                                "id": entity_id,
                                "name": callsign or icao24,
                                "lat": lat, "lng": lng,
                                "props": json.dumps({
                                    "icao24": icao24, "callsign": callsign,
                                    "origin_country": country,
                                }),
                            },
                        )
                        new_count += 1

                        # Publish new entity event
                        await redis_client.publish(
                            "nexus:ws:events",
                            json.dumps({"event": "entity:new", "data": {
                                "id": entity_id, "type": "Aircraft",
                                "name": callsign or icao24,
                                "confidence": 0.85, "sourceInt": "SIGINT",
                                "riskScore": 1.0,
                            }}),
                        )
                    else:
                        # Update position
                        await client.execute_write(
                            """MATCH (e:Entity {id: $id})
                               SET e.coordinates = point({latitude: $lat, longitude: $lng}),
                                   e.latitude = $lat, e.longitude = $lng,
                                   e.updatedAt = datetime()""",
                            {"id": entity_id, "lat": lat, "lng": lng},
                        )

                    # Build track point for WebSocket
                    activity = f"FL{int(altitude / 100) if altitude else 0} {int(velocity * 3.6)}km/h"
                    if callsign:
                        activity = f"{callsign} {activity}"

                    tracks.append({
                        "entityId": entity_id,
                        "position": {
                            "latitude": lat,
                            "longitude": lng,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "heading": heading,
                            "speed": velocity,
                            "activity": activity,
                            "activityType": "moving",
                            "entityType": "Aircraft",
                            "entityName": callsign or icao24,
                            "trigger": "adsb_scan",
                        },
                        "activity": activity,
                        "activityType": "moving",
                    })

                # Publish batch track update
                if tracks:
                    await redis_client.publish(
                        "nexus:ws:events",
                        json.dumps({"event": "track:batch_update", "data": {
                            "tracks": tracks,
                        }}),
                    )

                # Store scan metadata
                await redis_client.set("nexus:sigint:live_last_scan", json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "aircraft_count": len(tracks),
                    "new_entities": new_count,
                }))

                logger.info("sigint.area_scan.done",
                            aircraft=len(tracks), new=new_count)
            finally:
                await driver.close()
        finally:
            await redis_client.close()

    _run_async(_execute())
