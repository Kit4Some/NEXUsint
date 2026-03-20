"""Elasticsearch service for full-text entity search and autocomplete."""

import structlog
from elasticsearch import AsyncElasticsearch

logger = structlog.get_logger()

INDEX_NAME = "nexus-entities"

INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "edge_ngram_analyzer": {
                    "type": "custom",
                    "tokenizer": "edge_ngram_tokenizer",
                    "filter": ["lowercase"],
                },
                "search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"],
                },
            },
            "tokenizer": {
                "edge_ngram_tokenizer": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                    "token_chars": ["letter", "digit"],
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "name": {
                "type": "text",
                "analyzer": "edge_ngram_analyzer",
                "search_analyzer": "search_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "type": {"type": "keyword"},
            "source_int": {"type": "keyword"},
            "confidence": {"type": "float"},
            "risk_score": {"type": "float"},
            "description": {"type": "text"},
            "properties": {"type": "object", "enabled": False},
            "first_seen": {"type": "date"},
            "last_seen": {"type": "date"},
            "geo_point": {"type": "geo_point"},
            "suggest": {
                "type": "completion",
                "analyzer": "simple",
            },
        }
    },
}


class ElasticsearchService:
    def __init__(self, es_url: str):
        self._client = AsyncElasticsearch(hosts=[es_url])

    async def ensure_indices(self):
        """Create the entity index if it doesn't exist."""
        exists = await self._client.indices.exists(index=INDEX_NAME)
        if not exists:
            await self._client.indices.create(index=INDEX_NAME, body=INDEX_SETTINGS)
            logger.info("elasticsearch.index_created", index=INDEX_NAME)

    async def index_entity(self, entity_id: str, entity_data: dict):
        """Index or update a single entity document."""
        doc = {
            "id": entity_data.get("id", entity_id),
            "name": entity_data.get("name", ""),
            "type": entity_data.get("type", ""),
            "source_int": entity_data.get("sourceInt", entity_data.get("source_int", "")),
            "confidence": entity_data.get("confidence", 0.0),
            "risk_score": entity_data.get("riskScore", entity_data.get("risk_score", 0.0)),
            "description": entity_data.get("description", ""),
            "suggest": {"input": [entity_data.get("name", "")]},
        }
        await self._client.index(index=INDEX_NAME, id=entity_id, document=doc)

    async def bulk_index_entities(self, entities: list[dict]):
        """Bulk index multiple entities."""
        if not entities:
            return
        actions = []
        for entity in entities:
            eid = entity.get("id", "")
            actions.append({"index": {"_index": INDEX_NAME, "_id": eid}})
            actions.append({
                "id": eid,
                "name": entity.get("name", ""),
                "type": entity.get("type", ""),
                "source_int": entity.get("sourceInt", entity.get("source_int", "")),
                "confidence": entity.get("confidence", 0.0),
                "risk_score": entity.get("riskScore", entity.get("risk_score", 0.0)),
                "description": entity.get("description", ""),
                "suggest": {"input": [entity.get("name", "")]},
            })
        await self._client.bulk(operations=actions, refresh=True)
        logger.info("elasticsearch.bulk_indexed", count=len(entities))

    async def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        source_int: str | None = None,
        min_confidence: float | None = None,
        size: int = 50,
        offset: int = 0,
    ) -> dict:
        """Full-text entity search with optional filters."""
        must = []
        if query:
            must.append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "description", "type"],
                    "fuzziness": "AUTO",
                }
            })

        filters = []
        if entity_type:
            filters.append({"term": {"type": entity_type}})
        if source_int:
            filters.append({"term": {"source_int": source_int}})
        if min_confidence is not None:
            filters.append({"range": {"confidence": {"gte": min_confidence}}})

        body = {
            "query": {
                "bool": {
                    "must": must or [{"match_all": {}}],
                    "filter": filters,
                }
            },
            "from": offset,
            "size": size,
            "highlight": {
                "fields": {"name": {}, "description": {}},
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
            },
        }

        result = await self._client.search(index=INDEX_NAME, body=body)
        hits = result["hits"]
        return {
            "total": hits["total"]["value"],
            "hits": [
                {
                    **hit["_source"],
                    "score": hit["_score"],
                    "highlights": hit.get("highlight", {}),
                }
                for hit in hits["hits"]
            ],
        }

    async def suggest(self, prefix: str, size: int = 10) -> list[dict]:
        """Autocomplete suggestions using completion suggester."""
        body = {
            "suggest": {
                "entity-suggest": {
                    "prefix": prefix,
                    "completion": {
                        "field": "suggest",
                        "size": size,
                        "skip_duplicates": True,
                    },
                }
            }
        }
        result = await self._client.search(index=INDEX_NAME, body=body)
        suggestions = result.get("suggest", {}).get("entity-suggest", [{}])
        if not suggestions:
            return []
        return [
            {"id": opt["_source"]["id"], "name": opt["_source"]["name"], "type": opt["_source"]["type"]}
            for opt in suggestions[0].get("options", [])
        ]

    async def delete_entity(self, entity_id: str):
        """Remove entity from index."""
        try:
            await self._client.delete(index=INDEX_NAME, id=entity_id)
        except Exception:
            pass

    async def sync_from_neo4j(self, neo4j_driver):
        """Full reindex from Neo4j graph."""
        from neo4j import AsyncSession

        await self.ensure_indices()

        async with neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity) RETURN e.id AS id, e.name AS name, e.type AS type, "
                "e.sourceInt AS sourceInt, e.confidence AS confidence, "
                "e.riskScore AS riskScore LIMIT 10000"
            )
            records = await result.data()

        if records:
            await self.bulk_index_entities(records)
            logger.info("elasticsearch.sync_complete", count=len(records))
        return len(records)

    async def close(self):
        await self._client.close()
