"""Unified search endpoints — full-text (Elasticsearch) and semantic (pgvector)."""

from fastapi import APIRouter, Depends, HTTPException, status

from nexus.dependencies import get_elasticsearch, get_vector_search, get_neo4j
from nexus.api.middleware.rbac import require_admin

router = APIRouter()


@router.get("/fulltext")
async def fulltext_search(
    q: str,
    type: str | None = None,
    source_int: str | None = None,
    min_confidence: float | None = None,
    limit: int = 50,
    offset: int = 0,
    es=Depends(get_elasticsearch),
):
    """Full-text entity search via Elasticsearch."""
    return await es.search_entities(
        query=q,
        entity_type=type,
        source_int=source_int,
        min_confidence=min_confidence,
        size=limit,
        offset=offset,
    )


@router.get("/semantic")
async def semantic_search(
    q: str,
    top_k: int = 20,
    threshold: float = 0.7,
    vs=Depends(get_vector_search),
):
    """Semantic similarity search via pgvector."""
    try:
        return await vs.search_similar(query=q, top_k=top_k, threshold=threshold)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/suggest")
async def autocomplete(
    prefix: str,
    size: int = 10,
    es=Depends(get_elasticsearch),
):
    """Autocomplete suggestions for entity names."""
    return await es.suggest(prefix=prefix, size=size)


@router.post("/reindex")
async def reindex(
    _user=Depends(require_admin),
    es=Depends(get_elasticsearch),
    driver=Depends(get_neo4j),
):
    """Admin-only: trigger full reindex from Neo4j to Elasticsearch."""
    count = await es.sync_from_neo4j(driver)
    return {"detail": f"Reindexed {count} entities"}
