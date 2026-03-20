"""Entity management routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from nexus.dependencies import get_neo4j
from nexus.api.middleware.rbac import require_analyst
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.repository import EntityRepository
from nexus.models.entity import (
    EntityCreate,
    EntityFilter,
    EntityResponse,
    EntityType,
    RelationshipCreate,
    RelationshipResponse,
    SubGraphResponse,
    TimelineEvent,
)

router = APIRouter()


def _get_repository(driver=Depends(get_neo4j)) -> EntityRepository:
    return EntityRepository(Neo4jClient(driver))


@router.get("", response_model=list[EntityResponse])
async def search_entities(
    type: EntityType | None = None,
    q: str | None = Query(None, description="Search query"),
    source_int: str | None = None,
    min_confidence: float | None = None,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    repo: EntityRepository = Depends(_get_repository),
):
    """Search entities with optional filters."""
    filters = EntityFilter(
        type=type,
        query=q,
        source_int=source_int,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )
    return await repo.search_entities(filters)


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    repo: EntityRepository = Depends(_get_repository),
):
    """Get entity details by ID."""
    entity = await repo.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("/{entity_id}/graph", response_model=SubGraphResponse)
async def get_entity_graph(
    entity_id: str,
    depth: int = Query(2, ge=1, le=4),
    repo: EntityRepository = Depends(_get_repository),
):
    """Get N-hop subgraph around an entity."""
    return await repo.get_subgraph(entity_id, depth)


@router.get("/{entity_id}/timeline", response_model=list[TimelineEvent])
async def get_entity_timeline(
    entity_id: str,
    repo: EntityRepository = Depends(_get_repository),
):
    """Get time-ordered events related to an entity."""
    return await repo.get_entity_timeline(entity_id)


@router.post("", response_model=EntityResponse, status_code=201)
async def create_entity(
    entity: EntityCreate,
    _user=Depends(require_analyst),
    repo: EntityRepository = Depends(_get_repository),
):
    """Create a new entity."""
    return await repo.create_entity(entity)


@router.post("/resolve", response_model=EntityResponse)
async def resolve_entities(
    source_id: str,
    target_id: str,
    _user=Depends(require_analyst),
    repo: EntityRepository = Depends(_get_repository),
):
    """Merge two entities (manual entity resolution)."""
    result = await repo.merge_entities(source_id, target_id)
    if not result:
        raise HTTPException(status_code=404, detail="Entity not found after merge")
    return result


@router.post("/relationships", response_model=RelationshipResponse, status_code=201)
async def create_relationship(
    rel: RelationshipCreate,
    repo: EntityRepository = Depends(_get_repository),
):
    """Create a new relationship between entities."""
    return await repo.create_relationship(rel)


@router.post("/{entity_id}/dossier")
async def generate_dossier(
    entity_id: str,
    driver=Depends(get_neo4j),
) -> dict[str, Any]:
    """Generate an LLM-powered intelligence dossier for an entity."""
    from nexus.services.dossier_engine import DossierEngine

    client = Neo4jClient(driver)
    engine = DossierEngine(client)
    result = await engine.generate_dossier(entity_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{entity_id}/suggestions")
async def get_entity_suggestions(
    entity_id: str,
    repo: EntityRepository = Depends(_get_repository),
) -> dict[str, Any]:
    """Get suggested follow-up collection actions for an entity."""
    entity = await repo.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    from nexus.tasks.collection_tasks import get_pivot_suggestions
    try:
        from nexus.dependencies import lifespan_state
        if lifespan_state.pg_pool:
            async with lifespan_state.pg_pool.acquire() as conn:
                suggestions = await get_pivot_suggestions(
                    entity_id, entity.type.value, entity.name, conn,
                )
        else:
            # PG unavailable — return all possible suggestions without dedup
            suggestions = _get_all_suggestions(entity.type.value, entity.name)
    except Exception:
        suggestions = _get_all_suggestions(entity.type.value, entity.name)
    return {"entity_id": entity_id, "suggestions": suggestions}


def _get_all_suggestions(entity_type: str, entity_name: str) -> list[dict[str, str]]:
    """Return all pivot rules for an entity type without checking PG history."""
    from nexus.tasks.collection_tasks import _PIVOT_RULES
    rules = _PIVOT_RULES.get(entity_type, [])
    return [
        {
            "int_type": r["int_type"],
            "scan_type": r["scan_type"],
            "query": entity_name,
            "reason": f"Suggested {r['scan_type']} scan for {entity_type}",
        }
        for r in rules
    ]
