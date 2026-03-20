"""GraphQL resolver implementations."""

from typing import Optional

from nexus.dependencies import lifespan_state
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.repository import EntityRepository
from nexus.models.entity import EntityFilter, EntityType


async def _get_repo() -> EntityRepository:
    assert lifespan_state.neo4j_driver is not None
    return EntityRepository(Neo4jClient(lifespan_state.neo4j_driver))


def _to_entity_gql(entity):
    """Convert an EntityResponse to the GraphQL type dict."""
    from nexus.api.graphql.schema import EntityGQL, GeoPointGQL
    import json

    location = None
    if entity.latitude is not None and entity.longitude is not None:
        location = GeoPointGQL(latitude=entity.latitude, longitude=entity.longitude)

    return EntityGQL(
        id=entity.id,
        type=entity.type.value if hasattr(entity.type, "value") else str(entity.type),
        name=entity.name,
        properties=json.dumps(entity.properties),
        confidence=entity.confidence,
        source_int=entity.source_int,
        risk_score=entity.risk_score,
        location=location,
        first_seen=entity.first_seen,
        last_seen=entity.last_seen,
    )


async def resolve_entity(entity_id: str):
    repo = await _get_repo()
    entity = await repo.get_entity(entity_id)
    if not entity:
        return None
    return _to_entity_gql(entity)


async def resolve_entities(filter_input=None):
    repo = await _get_repo()
    filters = EntityFilter()
    if filter_input:
        if filter_input.type:
            filters.type = EntityType(filter_input.type)
        filters.query = filter_input.query
        filters.source_int = filter_input.source_int
        filters.min_confidence = filter_input.min_confidence
        filters.limit = filter_input.limit
        filters.offset = filter_input.offset

    entities = await repo.search_entities(filters)
    return [_to_entity_gql(e) for e in entities]


async def resolve_map_entities(bbox, types=None):
    repo = await _get_repo()
    results = await repo.get_entities_by_bbox(
        bbox.west, bbox.south, bbox.east, bbox.north, types
    )
    from nexus.api.graphql.schema import EntityGQL, GeoPointGQL

    return [
        EntityGQL(
            id=r["id"],
            type=r["type"],
            name=r["name"],
            properties="{}",
            confidence=r["confidence"],
            source_int=r["source_int"],
            risk_score=r.get("risk_score", 0),
            location=GeoPointGQL(latitude=r["latitude"], longitude=r["longitude"]),
        )
        for r in results
    ]


async def resolve_graph_neighbors(entity_id: str, depth: int = 2):
    from nexus.api.graphql.schema import SubGraphGQL, RelationshipGQL

    repo = await _get_repo()
    subgraph = await repo.get_subgraph(entity_id, depth)

    nodes = [_to_entity_gql(n) for n in subgraph.nodes]
    edges = [
        RelationshipGQL(
            id=e.id,
            type=e.type,
            source_id=e.source_id,
            target_id=e.target_id,
            confidence=e.confidence,
            source_int=e.source_int,
            timestamp=e.timestamp,
        )
        for e in subgraph.edges
    ]

    return SubGraphGQL(nodes=nodes, edges=edges)


async def resolve_create_investigation(input_data):
    from nexus.api.graphql.schema import InvestigationGQL
    from datetime import datetime

    # Simplified: in full implementation, use PostgreSQL
    return InvestigationGQL(
        id="inv-placeholder",
        query=input_data.query,
        status="created",
        priority=input_data.priority,
        progress=0,
        entity_count=0,
        created_at=datetime.utcnow(),
    )


async def resolve_merge_entities(source_id: str, target_id: str):
    repo = await _get_repo()
    result = await repo.merge_entities(source_id, target_id)
    if not result:
        return None
    return _to_entity_gql(result)
