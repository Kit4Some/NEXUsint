"""Strawberry GraphQL schema for NEXUS."""

from typing import Optional
from datetime import datetime
from enum import Enum
import json

import strawberry
from strawberry.fastapi import GraphQLRouter

from nexus.api.graphql.resolvers import (
    resolve_entity,
    resolve_entities,
    resolve_map_entities,
    resolve_graph_neighbors,
    resolve_create_investigation,
    resolve_merge_entities,
)


@strawberry.enum
class EntityTypeGQL(Enum):
    Person = "Person"
    Organization = "Organization"
    Location = "Location"
    Event = "Event"
    IPAddress = "IPAddress"
    Domain = "Domain"
    Certificate = "Certificate"
    ThreatActor = "ThreatActor"
    Malware = "Malware"
    Vulnerability = "Vulnerability"
    Indicator = "Indicator"


@strawberry.enum
class IntTypeGQL(Enum):
    SOCMINT = "SOCMINT"
    GEOINT = "GEOINT"
    SIGINT = "SIGINT"
    CYBINT = "CYBINT"


@strawberry.type
class GeoPointGQL:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None


@strawberry.type
class RelationshipGQL:
    id: str
    type: str
    source_id: str
    target_id: str
    confidence: float
    source_int: str
    timestamp: Optional[datetime] = None


@strawberry.type
class EntityGQL:
    id: str
    type: str
    name: str
    properties: str  # JSON string
    confidence: float
    source_int: str
    risk_score: float
    location: Optional[GeoPointGQL] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


@strawberry.type
class SubGraphGQL:
    nodes: list[EntityGQL]
    edges: list[RelationshipGQL]


@strawberry.type
class InvestigationGQL:
    id: str
    query: str
    status: str
    priority: str
    progress: int
    entity_count: int
    created_at: datetime


@strawberry.input
class EntityFilterInput:
    type: Optional[str] = None
    query: Optional[str] = None
    source_int: Optional[str] = None
    min_confidence: Optional[float] = None
    limit: int = 50
    offset: int = 0


@strawberry.input
class BBoxInput:
    west: float
    south: float
    east: float
    north: float


@strawberry.input
class InvestigationInput:
    query: str
    target_ints: list[str]
    priority: str = "medium"


@strawberry.type
class Query:
    @strawberry.field
    async def entity(self, id: str) -> Optional[EntityGQL]:
        return await resolve_entity(id)

    @strawberry.field
    async def entities(
        self, filter: Optional[EntityFilterInput] = None
    ) -> list[EntityGQL]:
        return await resolve_entities(filter)

    @strawberry.field
    async def map_entities(
        self, bbox: BBoxInput, types: Optional[list[str]] = None
    ) -> list[EntityGQL]:
        return await resolve_map_entities(bbox, types)

    @strawberry.field
    async def graph_neighbors(
        self, entity_id: str, depth: int = 2
    ) -> SubGraphGQL:
        return await resolve_graph_neighbors(entity_id, depth)


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_investigation(
        self, input: InvestigationInput
    ) -> InvestigationGQL:
        return await resolve_create_investigation(input)

    @strawberry.mutation
    async def merge_entities(
        self, source_id: str, target_id: str
    ) -> Optional[EntityGQL]:
        return await resolve_merge_entities(source_id, target_id)


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)
