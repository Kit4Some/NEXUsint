"""Celery tasks for Elasticsearch indexing and vector embedding."""

import asyncio
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


@app.task(name="nexus.tasks.indexing_tasks.index_entities")
def index_entities(entity_ids: list[str]):
    """Index a batch of entities into Elasticsearch and generate pgvector embeddings."""
    logger.info("indexing_task.index_entities", count=len(entity_ids))

    async def _execute():
        from neo4j import AsyncGraphDatabase
        import asyncpg
        from nexus.config import settings
        from nexus.services.elasticsearch import ElasticsearchService
        from nexus.services.vector_search import VectorSearchService

        es = ElasticsearchService(settings.elasticsearch_url)
        await es.ensure_indices()

        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

        try:
            # Fetch entities from Neo4j
            async with driver.session() as session:
                result = await session.run(
                    "MATCH (e:Entity) WHERE e.id IN $ids "
                    "RETURN e.id AS id, e.name AS name, e.type AS type, "
                    "e.sourceInt AS sourceInt, e.confidence AS confidence, "
                    "e.riskScore AS riskScore, e.description AS description",
                    {"ids": entity_ids},
                )
                records = await result.data()

            if not records:
                return

            # Index into Elasticsearch
            await es.bulk_index_entities(records)

            # Generate vector embeddings
            if settings.openai_api_key:
                pool = await asyncpg.create_pool(dsn=settings.get_postgres_dsn(), min_size=1, max_size=2)
                try:
                    vs = VectorSearchService(pool, settings.openai_api_key)
                    await vs.bulk_embed_entities(records)
                finally:
                    await pool.close()

            logger.info("indexing_task.index_entities.done", count=len(records))

        finally:
            await es.close()
            await driver.close()

    _run_async(_execute())


@app.task(name="nexus.tasks.indexing_tasks.full_reindex")
def full_reindex():
    """Full reindex from Neo4j to Elasticsearch."""
    logger.info("indexing_task.full_reindex.started")

    async def _execute():
        from neo4j import AsyncGraphDatabase
        from nexus.config import settings
        from nexus.services.elasticsearch import ElasticsearchService

        es = ElasticsearchService(settings.elasticsearch_url)
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

        try:
            count = await es.sync_from_neo4j(driver)
            logger.info("indexing_task.full_reindex.done", count=count)
            return {"count": count}
        finally:
            await es.close()
            await driver.close()

    return _run_async(_execute())
