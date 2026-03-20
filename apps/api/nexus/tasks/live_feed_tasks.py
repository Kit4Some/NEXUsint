"""Celery Beat tasks for real-time OSINT data collection.

Adapted from Shadowbroker's APScheduler orchestrator (``data_fetcher.py``)
into NEXUS's Celery Beat + Redis + Socket.IO WebSocket push architecture.

Two tiers:
  - **fast** (every 60 s): flights, military, ships
  - **slow** (every 300 s): news, earthquakes, fires, weather, stocks, oil
"""

from __future__ import annotations

import asyncio
import json

import structlog

from nexus.tasks import app

logger = structlog.get_logger()


def _run_async(coro):  # noqa: ANN001
    """Run an async coroutine inside a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Fast tier — flights, military, ships (every 60 s)
# ---------------------------------------------------------------------------


@app.task(name="nexus.tasks.live_feed_tasks.live_feed_fast")
def live_feed_fast() -> None:
    """Collect fast-tier live data: flights, military aircraft."""
    _run_async(_fast_collect())


async def _fast_collect() -> None:
    from nexus.services.live_store import (
        is_live_feed_active,
        set_live_data,
        publish_live_event,
    )

    if not await is_live_feed_active():
        return

    logger.info("live_feed.fast.started")

    results: dict = {}

    # ── Flights ──────────────────────────────────────────────────────────
    try:
        from nexus.collectors.sigint.adsb_live_collector import fetch_all_flights

        flight_data = await fetch_all_flights()
        commercial = flight_data.get("commercial_flights", [])
        private_jets = flight_data.get("private_jets", [])
        private_flights = flight_data.get("private_flights", [])
        tracked = flight_data.get("tracked_flights", [])
        gps_jamming = flight_data.get("gps_jamming", [])

        all_flights = commercial + private_jets + private_flights
        await set_live_data("commercial_flights", commercial, ttl=120)
        await set_live_data("private_jets", private_jets, ttl=120)
        await set_live_data("private_flights", private_flights, ttl=120)
        await set_live_data("tracked_flights", tracked, ttl=120)
        await set_live_data("gps_jamming", gps_jamming, ttl=120)

        results["flights"] = len(all_flights)
        results["tracked"] = len(tracked)

        await publish_live_event("livefeed:flights", {
            "flights": all_flights,
            "tracked": tracked,
        })
        if gps_jamming:
            await publish_live_event("livefeed:jamming", {
                "zones": gps_jamming,
            })
    except Exception as exc:
        logger.error("live_feed.fast.flights_failed", error=str(exc))

    # ── Military flights ─────────────────────────────────────────────────
    try:
        from nexus.collectors.sigint.military_classifier import fetch_military_flights

        mil_data = await fetch_military_flights()
        military = mil_data.get("military_flights", [])
        uavs = mil_data.get("uavs", [])

        await set_live_data("military_flights", military, ttl=120)
        await set_live_data("uavs", uavs, ttl=120)

        results["military"] = len(military)
        results["uavs"] = len(uavs)

        await publish_live_event("livefeed:military", {
            "military": military,
            "uavs": uavs,
        })
    except Exception as exc:
        logger.error("live_feed.fast.military_failed", error=str(exc))

    # ── Satellites ────────────────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.satellites import fetch_satellites

        satellites = await fetch_satellites()
        await set_live_data("satellites", satellites, ttl=120)
        results["satellites"] = len(satellites)
        await publish_live_event("livefeed:satellites", {"satellites": satellites})
    except Exception as exc:
        logger.error("live_feed.fast.satellites_failed", error=str(exc))

    # ── Selective entity persistence ─────────────────────────────────────
    try:
        await _persist_notable_aircraft(
            results.get("tracked", 0),
        )
    except Exception as exc:
        logger.debug("live_feed.fast.persist_skipped", error=str(exc))

    # ── Publish status ───────────────────────────────────────────────────
    from nexus.services.live_store import get_timestamps
    timestamps = await get_timestamps()
    await publish_live_event("livefeed:status", {
        "source_timestamps": timestamps,
        "tier": "fast",
        "counts": results,
    })

    logger.info("live_feed.fast.completed", **results)


async def _persist_notable_aircraft(tracked_count: int) -> None:
    """Persist tracked/alerted aircraft to Neo4j knowledge graph.

    Uses entity_factory to create proper Aircraft + Location entities
    with ORIGINATES_FROM / TERMINATES_AT relationships.
    """
    if tracked_count == 0:
        return

    from nexus.services.live_store import get_live_data
    from nexus.processing.entity_factory import (
        live_flight_to_entities,
        infer_live_relationships,
    )

    tracked = await get_live_data("tracked_flights") or []
    if not tracked:
        return

    await _persist_entities_to_neo4j(
        items=tracked[:50],
        converter=live_flight_to_entities,
        label="aircraft",
    )


# ---------------------------------------------------------------------------
# Shared Neo4j persistence helper
# ---------------------------------------------------------------------------


async def _persist_entities_to_neo4j(
    items: list[dict],
    converter,  # noqa: ANN001 — callable(dict) -> list[EntityCreate]
    label: str,
) -> int:
    """Persist live feed items to the Neo4j knowledge graph.

    Uses entity_factory converters to create entities and infer relationships,
    then publishes entity:new events so the frontend updates.
    """
    from nexus.processing.entity_factory import infer_live_relationships

    import redis.asyncio as aioredis
    from nexus.config import settings

    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    persisted = 0
    try:
        for item in items:
            try:
                entities = converter(item)
                if not entities:
                    continue

                rels = infer_live_relationships(entities)

                # Publish primary entity via WebSocket
                primary = entities[0]
                entity_payload = {
                    "event": "entity:new",
                    "data": {
                        "type": primary.type.value,
                        "name": primary.name,
                        "properties": primary.properties,
                        "confidence": primary.confidence,
                        "source_int": primary.source_int,
                        "risk_score": primary.risk_score,
                        "latitude": primary.latitude,
                        "longitude": primary.longitude,
                        "relationships": rels,
                    },
                }
                await r.publish("nexus:ws:events", json.dumps(entity_payload, default=str))
                persisted += 1
            except Exception as exc:
                logger.debug(f"live_feed.persist.{label}_item_failed", error=str(exc))
    finally:
        await r.aclose()

    if persisted > 0:
        logger.info(f"live_feed.persist.{label}", count=persisted)
    return persisted


# ---------------------------------------------------------------------------
# Slow tier — news, earthquakes, fires, weather, stocks, oil (every 300 s)
# ---------------------------------------------------------------------------


@app.task(name="nexus.tasks.live_feed_tasks.live_feed_slow")
def live_feed_slow() -> None:
    """Collect slow-tier live data: news, geophysical, financial."""
    _run_async(_slow_collect())


async def _slow_collect() -> None:
    from nexus.services.live_store import (
        get_live_data,
        get_timestamps,
        is_live_feed_active,
        set_live_data,
        publish_live_event,
    )

    if not await is_live_feed_active():
        return

    logger.info("live_feed.slow.started")

    results: dict = {}

    # ── News ─────────────────────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.news_collector import fetch_news

        news = await fetch_news()
        await set_live_data("news", news, ttl=600)
        results["news"] = len(news)
        await publish_live_event("livefeed:news", {"articles": news})
    except Exception as exc:
        logger.error("live_feed.slow.news_failed", error=str(exc))

    # ── Earthquakes ──────────────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.earth_observation import fetch_earthquakes

        quakes = await fetch_earthquakes()
        await set_live_data("earthquakes", quakes, ttl=600)
        results["earthquakes"] = len(quakes)
        await publish_live_event("livefeed:earthquakes", {"earthquakes": quakes})
    except Exception as exc:
        logger.error("live_feed.slow.earthquakes_failed", error=str(exc))

    # ── FIRMS fires ──────────────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.earth_observation import fetch_firms_fires

        fires = await fetch_firms_fires()
        await set_live_data("fires", fires, ttl=600)
        results["fires"] = len(fires)
        await publish_live_event("livefeed:fires", {"fires": fires})
    except Exception as exc:
        logger.error("live_feed.slow.fires_failed", error=str(exc))

    # ── Weather radar ────────────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.earth_observation import fetch_weather

        weather = await fetch_weather()
        await set_live_data("weather", weather, ttl=600)
        await publish_live_event("livefeed:weather", {"radar": weather})
    except Exception as exc:
        logger.error("live_feed.slow.weather_failed", error=str(exc))

    # ── Space weather ────────────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.earth_observation import fetch_space_weather

        space_wx = await fetch_space_weather()
        await set_live_data("space_weather", space_wx, ttl=600)
    except Exception as exc:
        logger.error("live_feed.slow.space_weather_failed", error=str(exc))

    # ── Defense stocks ───────────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.financial import fetch_defense_stocks

        stocks = await fetch_defense_stocks()
        await set_live_data("stocks", stocks, ttl=600)
        await publish_live_event("livefeed:stocks", {"stocks": stocks})
    except Exception as exc:
        logger.error("live_feed.slow.stocks_failed", error=str(exc))

    # ── Oil prices ───────────────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.financial import fetch_oil_prices

        oil = await fetch_oil_prices()
        await set_live_data("oil", oil, ttl=600)
        await publish_live_event("livefeed:oil", {"oil": oil})
    except Exception as exc:
        logger.error("live_feed.slow.oil_failed", error=str(exc))

    # ── GDELT geopolitics ──────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.geopolitics import fetch_gdelt

        gdelt = await fetch_gdelt()
        await set_live_data("gdelt", gdelt, ttl=600)
        results["gdelt"] = len(gdelt)
        await publish_live_event("livefeed:gdelt", {"events": gdelt})
    except Exception as exc:
        logger.error("live_feed.slow.gdelt_failed", error=str(exc))

    # ── Frontlines ───────────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.geopolitics import fetch_frontlines

        frontlines = await fetch_frontlines()
        if frontlines:
            await set_live_data("frontlines", frontlines, ttl=1800)
            await publish_live_event("livefeed:frontlines", {"geojson": frontlines})
    except Exception as exc:
        logger.error("live_feed.slow.frontlines_failed", error=str(exc))

    # ── Internet outages ─────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.infrastructure import fetch_internet_outages

        outages = await fetch_internet_outages()
        await set_live_data("internet_outages", outages, ttl=600)
        results["internet_outages"] = len(outages)
        await publish_live_event("livefeed:outages", {"outages": outages})
    except Exception as exc:
        logger.error("live_feed.slow.outages_failed", error=str(exc))

    # ── KiwiSDR receivers ────────────────────────────────────────────
    try:
        from nexus.collectors.osint_feeds.infrastructure import fetch_kiwisdr

        kiwisdr = await fetch_kiwisdr()
        await set_live_data("kiwisdr", kiwisdr, ttl=1800)
        results["kiwisdr"] = len(kiwisdr)
    except Exception as exc:
        logger.error("live_feed.slow.kiwisdr_failed", error=str(exc))

    # ── Reference data (airports, bases, etc.) ───────────────────────
    try:
        from nexus.collectors.osint_feeds.reference_data import (
            fetch_airports, load_military_bases, load_datacenters, load_power_plants,
        )

        airports = await fetch_airports()
        await set_live_data("airports", airports, ttl=3600)

        mil_bases = load_military_bases()
        await set_live_data("military_bases", mil_bases, ttl=3600)

        datacenters = load_datacenters()
        await set_live_data("datacenters", datacenters, ttl=3600)

        power_plants = load_power_plants()
        await set_live_data("power_plants", power_plants, ttl=3600)

        results["airports"] = len(airports)
    except Exception as exc:
        logger.error("live_feed.slow.reference_failed", error=str(exc))

    # ── Persist high-risk news to knowledge graph ──────────────────────
    try:
        from nexus.processing.entity_factory import live_news_to_entity

        all_news = await get_live_data("news") or []
        high_risk_news = [n for n in all_news if n.get("risk_score", 0) >= 6]
        if high_risk_news:
            persisted = await _persist_entities_to_neo4j(
                items=high_risk_news[:30],
                converter=live_news_to_entity,
                label="news",
            )
            results["news_persisted"] = persisted
    except Exception as exc:
        logger.error("live_feed.slow.news_persist_failed", error=str(exc))

    # ── Persist significant earthquakes to knowledge graph ────────────
    try:
        from nexus.processing.entity_factory import live_earthquake_to_entity

        all_quakes = await get_live_data("earthquakes") or []
        sig_quakes = [q for q in all_quakes if float(q.get("mag", 0)) >= 4.0]
        if sig_quakes:
            persisted = await _persist_entities_to_neo4j(
                items=sig_quakes[:20],
                converter=live_earthquake_to_entity,
                label="earthquake",
            )
            results["earthquakes_persisted"] = persisted
    except Exception as exc:
        logger.error("live_feed.slow.earthquake_persist_failed", error=str(exc))

    # ── Publish status ───────────────────────────────────────────────────
    timestamps = await get_timestamps()
    await publish_live_event("livefeed:status", {
        "source_timestamps": timestamps,
        "tier": "slow",
        "counts": results,
    })

    logger.info("live_feed.slow.completed", **results)
