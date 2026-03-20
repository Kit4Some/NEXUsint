"""CRUD operations for the Neo4j knowledge graph."""

import ast
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

import structlog

from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.services.cache import CacheService
from nexus.models.entity import (
    EntityCreate,
    EntityFilter,
    EntityResponse,
    RelationshipCreate,
    RelationshipResponse,
    SubGraphResponse,
    TimelineEvent,
)

logger = structlog.get_logger()


def _parse_properties(raw: Any) -> dict[str, Any]:
    """Parse properties stored as string (Python repr or JSON) back to dict."""
    if isinstance(raw, dict):
        return raw
    if not raw or not isinstance(raw, str):
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        result = ast.literal_eval(raw)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass
    return {}


def _to_datetime(val: Any) -> datetime:
    """Convert neo4j.time.DateTime or other types to Python datetime."""
    if isinstance(val, datetime):
        return val
    if val is None:
        return datetime.utcnow()
    # neo4j.time.DateTime has .to_native() method
    if hasattr(val, 'to_native'):
        return val.to_native()
    # Try ISO format string
    if isinstance(val, str):
        return datetime.fromisoformat(val.replace('Z', '+00:00'))
    return datetime.utcnow()


class EntityRepository:
    """Repository for entity CRUD operations on Neo4j."""

    def __init__(self, client: Neo4jClient, cache: CacheService | None = None) -> None:
        self._client = client
        self._cache = cache

    async def create_entity(self, entity: EntityCreate) -> EntityResponse:
        """Create a new entity node in the knowledge graph."""
        entity_id = f"{entity.type.value.lower()}-{uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        query = """
        CREATE (e:Entity:%s {
            id: $id,
            name: $name,
            type: $type,
            properties: $properties,
            confidence: $confidence,
            sourceInt: $source_int,
            riskScore: $risk_score,
            firstSeen: datetime($now),
            lastSeen: datetime($now),
            createdAt: datetime($now),
            updatedAt: datetime($now)
        })
        RETURN e
        """ % entity.type.value

        params = {
            "id": entity_id,
            "name": entity.name,
            "type": entity.type.value,
            "properties": json.dumps(entity.properties),
            "confidence": entity.confidence,
            "source_int": entity.source_int,
            "risk_score": entity.risk_score,
            "now": now,
        }

        # Add coordinates if provided
        if entity.latitude is not None and entity.longitude is not None:
            query = """
            CREATE (e:Entity:%s {
                id: $id,
                name: $name,
                type: $type,
                properties: $properties,
                confidence: $confidence,
                sourceInt: $source_int,
                riskScore: $risk_score,
                coordinates: point({latitude: $lat, longitude: $lon}),
                firstSeen: datetime($now),
                lastSeen: datetime($now),
                createdAt: datetime($now),
                updatedAt: datetime($now)
            })
            RETURN e
            """ % entity.type.value
            params["lat"] = entity.latitude
            params["lon"] = entity.longitude

        records = await self._client.execute_write(query, params)
        logger.info("entity.created", entity_id=entity_id, type=entity.type.value)

        # Invalidate caches after entity creation
        if self._cache:
            await self._cache.invalidate_pattern("search:*")
            await self._cache.invalidate_analytics()

        return EntityResponse(
            id=entity_id,
            name=entity.name,
            type=entity.type,
            properties=entity.properties,
            confidence=entity.confidence,
            source_int=entity.source_int,
            risk_score=entity.risk_score,
            latitude=entity.latitude,
            longitude=entity.longitude,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def get_entity(self, entity_id: str) -> EntityResponse | None:
        """Get an entity by ID."""
        query = """
        MATCH (e:Entity {id: $id})
        RETURN e.id AS id, e.name AS name, e.type AS type,
               e.properties AS properties, e.confidence AS confidence,
               e.sourceInt AS source_int, e.riskScore AS risk_score,
               e.firstSeen AS first_seen, e.lastSeen AS last_seen,
               e.createdAt AS created_at, e.updatedAt AS updated_at
        """
        records = await self._client.execute_read(query, {"id": entity_id})
        if not records:
            return None

        r = records[0]
        return EntityResponse(
            id=r["id"],
            name=r["name"],
            type=r["type"],
            properties=_parse_properties(r.get("properties")),
            confidence=r["confidence"],
            source_int=r["source_int"],
            risk_score=r.get("risk_score", 0),
            first_seen=_to_datetime(r["first_seen"]),
            last_seen=_to_datetime(r["last_seen"]),
            created_at=_to_datetime(r["created_at"]),
            updated_at=_to_datetime(r["updated_at"]),
        )

    async def search_entities(self, filters: EntityFilter) -> list[EntityResponse]:
        """Search entities with filters."""
        conditions = []
        params: dict[str, Any] = {}

        if filters.type:
            conditions.append("e.type = $type")
            params["type"] = filters.type.value

        if filters.source_int:
            conditions.append("e.sourceInt = $source_int")
            params["source_int"] = filters.source_int

        if filters.min_confidence is not None:
            conditions.append("e.confidence >= $min_confidence")
            params["min_confidence"] = filters.min_confidence

        if filters.min_risk_score is not None:
            conditions.append("e.riskScore >= $min_risk_score")
            params["min_risk_score"] = filters.min_risk_score

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        if filters.query:
            query = f"""
            CALL db.index.fulltext.queryNodes('entity_search', $query)
            YIELD node AS e, score
            WHERE {where_clause}
            RETURN e.id AS id, e.name AS name, e.type AS type,
                   e.properties AS properties, e.confidence AS confidence,
                   e.sourceInt AS source_int, e.riskScore AS risk_score,
                   e.firstSeen AS first_seen, e.lastSeen AS last_seen,
                   e.createdAt AS created_at, e.updatedAt AS updated_at
            ORDER BY score DESC
            SKIP $offset LIMIT $limit
            """
            params["query"] = filters.query
        else:
            query = f"""
            MATCH (e:Entity)
            WHERE {where_clause}
            RETURN e.id AS id, e.name AS name, e.type AS type,
                   e.properties AS properties, e.confidence AS confidence,
                   e.sourceInt AS source_int, e.riskScore AS risk_score,
                   e.firstSeen AS first_seen, e.lastSeen AS last_seen,
                   e.createdAt AS created_at, e.updatedAt AS updated_at
            ORDER BY e.riskScore DESC, e.confidence DESC
            SKIP $offset LIMIT $limit
            """

        params["offset"] = filters.offset
        params["limit"] = filters.limit

        records = await self._client.execute_read(query, params)

        return [
            EntityResponse(
                id=r["id"],
                name=r["name"],
                type=r["type"],
                properties=_parse_properties(r.get("properties")),
                confidence=r["confidence"],
                source_int=r["source_int"],
                risk_score=r.get("risk_score", 0),
                first_seen=_to_datetime(r["first_seen"]),
                last_seen=_to_datetime(r["last_seen"]),
                created_at=_to_datetime(r["created_at"]),
                updated_at=_to_datetime(r["updated_at"]),
            )
            for r in records
        ]

    async def get_subgraph(self, entity_id: str, depth: int = 2) -> SubGraphResponse:
        """Get N-hop subgraph around an entity."""
        query = """
        MATCH path = (e:Entity {id: $id})-[r*1..%d]-(neighbor:Entity)
        WITH collect(DISTINCT neighbor) AS neighbors,
             collect(DISTINCT relationships(path)) AS all_rels,
             e
        UNWIND neighbors + [e] AS node
        WITH DISTINCT node, all_rels
        RETURN collect(DISTINCT {
            id: node.id, name: node.name, type: node.type,
            confidence: node.confidence, sourceInt: node.sourceInt,
            riskScore: node.riskScore,
            firstSeen: node.firstSeen, lastSeen: node.lastSeen,
            createdAt: node.createdAt, updatedAt: node.updatedAt
        }) AS nodes
        """ % min(depth, 4)

        records = await self._client.execute_read(query, {"id": entity_id})

        nodes = []
        if records and records[0].get("nodes"):
            for n in records[0]["nodes"]:
                nodes.append(
                    EntityResponse(
                        id=n["id"],
                        name=n["name"],
                        type=n["type"],
                        properties={},
                        confidence=n["confidence"],
                        source_int=n["sourceInt"],
                        risk_score=n.get("riskScore", 0),
                        first_seen=_to_datetime(n["firstSeen"]),
                        last_seen=_to_datetime(n["lastSeen"]),
                        created_at=_to_datetime(n["createdAt"]),
                        updated_at=_to_datetime(n["updatedAt"]),
                    )
                )

        # Get edges
        edge_query = """
        MATCH (e:Entity {id: $id})-[r*1..%d]-(neighbor:Entity)
        UNWIND r AS rel
        WITH DISTINCT rel
        RETURN type(rel) AS type,
               startNode(rel).id AS source_id,
               endNode(rel).id AS target_id,
               rel.confidence AS confidence,
               rel.source AS source_int,
               rel.method AS method,
               rel.timestamp AS timestamp
        """ % min(depth, 4)

        edge_records = await self._client.execute_read(edge_query, {"id": entity_id})
        edges = [
            RelationshipResponse(
                id=f"rel-{i}",
                type=r["type"],
                source_id=r["source_id"],
                target_id=r["target_id"],
                confidence=r.get("confidence", 0.5),
                source_int=r.get("source_int", ""),
                method=r.get("method", "manual"),
                timestamp=_to_datetime(r.get("timestamp")) if r.get("timestamp") else None,
            )
            for i, r in enumerate(edge_records)
        ]

        return SubGraphResponse(nodes=nodes, edges=edges)

    async def get_entity_timeline(self, entity_id: str) -> list[TimelineEvent]:
        """Get time-ordered events related to an entity."""
        query = """
        MATCH (e:Entity {id: $id})-[r]-(other:Entity)
        WHERE r.timestamp IS NOT NULL
        RETURN type(r) AS event_type,
               other.name AS title,
               r.source AS source_int,
               r.confidence AS confidence,
               r.timestamp AS timestamp,
               other.id AS entity_id
        ORDER BY r.timestamp DESC
        LIMIT 100
        """
        records = await self._client.execute_read(query, {"id": entity_id})

        return [
            TimelineEvent(
                timestamp=r["timestamp"],
                event_type=r["event_type"],
                title=f"{r['event_type']} → {r['title']}",
                description=f"Relationship with {r['title']}",
                source_int=r.get("source_int", ""),
                confidence=r.get("confidence", 0.5),
                entity_id=r.get("entity_id"),
            )
            for r in records
        ]

    async def create_relationship(self, rel: RelationshipCreate) -> RelationshipResponse:
        """Create a relationship between two entities."""
        rel_id = f"rel-{uuid4().hex[:12]}"

        query = f"""
        MATCH (source:Entity {{id: $source_id}})
        MATCH (target:Entity {{id: $target_id}})
        CREATE (source)-[r:{rel.type} {{
            confidence: $confidence,
            source: $source_int,
            method: $method,
            timestamp: datetime($timestamp)
        }}]->(target)
        RETURN type(r) AS type
        """

        params = {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "confidence": rel.confidence,
            "source_int": rel.source_int,
            "method": rel.method.value,
            "timestamp": (rel.timestamp or datetime.utcnow()).isoformat(),
        }

        await self._client.execute_write(query, params)
        logger.info("relationship.created", type=rel.type, source=rel.source_id, target=rel.target_id)

        # Invalidate caches after relationship creation
        if self._cache:
            await self._cache.invalidate_entity(rel.source_id)
            await self._cache.invalidate_entity(rel.target_id)
            await self._cache.invalidate_analytics()

        return RelationshipResponse(
            id=rel_id,
            type=rel.type,
            source_id=rel.source_id,
            target_id=rel.target_id,
            confidence=rel.confidence,
            source_int=rel.source_int,
            method=rel.method,
            timestamp=rel.timestamp,
        )

    async def get_entities_by_bbox(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
        entity_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get entities within a bounding box."""
        type_filter = ""
        params: dict[str, Any] = {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
        }

        if entity_types:
            type_filter = "AND e.type IN $types"
            params["types"] = entity_types

        query = f"""
        MATCH (e:Entity)
        WHERE e.coordinates IS NOT NULL
          AND point.withinBBox(
              e.coordinates,
              point({{latitude: $south, longitude: $west}}),
              point({{latitude: $north, longitude: $east}})
          )
          {type_filter}
        RETURN e.id AS id, e.name AS name, e.type AS type,
               e.coordinates.latitude AS latitude,
               e.coordinates.longitude AS longitude,
               e.confidence AS confidence, e.sourceInt AS source_int,
               e.riskScore AS risk_score
        LIMIT 1000
        """

        return await self._client.execute_read(query, params)

    async def merge_entities(self, source_id: str, target_id: str) -> EntityResponse | None:
        """Merge two entities — keep target, transfer relationships from source, delete source."""
        query = """
        MATCH (source:Entity {id: $source_id})
        MATCH (target:Entity {id: $target_id})
        // Transfer all outgoing relationships
        OPTIONAL MATCH (source)-[r_out]->(other)
        WHERE other.id <> target.id
        FOREACH (_ IN CASE WHEN r_out IS NOT NULL THEN [1] ELSE [] END |
            CREATE (target)-[new_r:DERIVED_FROM]->(other)
        )
        // Transfer all incoming relationships
        OPTIONAL MATCH (other2)-[r_in]->(source)
        WHERE other2.id <> target.id
        FOREACH (_ IN CASE WHEN r_in IS NOT NULL THEN [1] ELSE [] END |
            CREATE (other2)-[new_r2:DERIVED_FROM]->(target)
        )
        // Create SAME_AS link then detach delete source
        CREATE (target)-[:SAME_AS {
            confidence: 1.0,
            source: 'FUSION/ManualMerge',
            timestamp: datetime(),
            method: 'manual'
        }]->(source)
        SET target.updatedAt = datetime()
        DETACH DELETE source
        RETURN target.id AS id
        """

        await self._client.execute_write(query, {"source_id": source_id, "target_id": target_id})

        # Invalidate caches after merge
        if self._cache:
            await self._cache.invalidate_entity(source_id)
            await self._cache.invalidate_entity(target_id)
            await self._cache.invalidate_pattern("search:*")
            await self._cache.invalidate_analytics()

        return await self.get_entity(target_id)
