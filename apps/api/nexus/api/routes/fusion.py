"""Fusion routes — cross-INT correlation, evidence combination, D-S analysis."""

from fastapi import APIRouter, Depends, Query

from nexus.dependencies import get_neo4j
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.repository import EntityRepository
from nexus.fusion.cross_int_correlator import CrossIntCorrelator
from nexus.fusion.evidence_combiner import EvidenceCombiner

router = APIRouter()


@router.get("/correlation-matrix")
async def get_correlation_matrix(driver=Depends(get_neo4j)):
    """Get the 4x4 cross-INT correlation count matrix."""
    client = Neo4jClient(driver)

    # Fetch all entities with source_int
    records = await client.execute_read("""
        MATCH (e:Entity)
        WHERE e.sourceInt IS NOT NULL AND e.id IS NOT NULL
        RETURN e.id AS id, e.name AS name, e.type AS type,
               e.sourceInt AS source_int,
               e.firstSeen AS first_seen
        LIMIT 2000
    """)

    entity_dicts = [
        {
            "id": r.get("id", ""),
            "name": r.get("name", ""),
            "type": r.get("type", ""),
            "source_int": r.get("source_int", ""),
            "first_seen": str(r.get("first_seen", "")) if r.get("first_seen") else None,
        }
        for r in records
    ]

    correlator = CrossIntCorrelator()
    matrix = correlator.compute_correlation_matrix(entity_dicts)

    return {"matrix": matrix, "entity_count": len(entity_dicts)}


@router.get("/entity/{entity_id}/evidence")
async def get_entity_evidence(entity_id: str, driver=Depends(get_neo4j)):
    """Get combined evidence and Admiralty grade for an entity."""
    client = Neo4jClient(driver)
    repo = EntityRepository(client)

    entity = await repo.get_entity(entity_id)
    if not entity:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Entity not found")

    # Get related entities to build evidence
    subgraph = await repo.get_subgraph(entity_id, depth=1)

    combiner = EvidenceCombiner()
    # Build minimal evidence from subgraph nodes
    from nexus.collectors.base import CollectionResult
    from datetime import datetime

    sources = []
    for node in subgraph.nodes:
        sources.append(CollectionResult(
            source_int=node.source_int,
            source_id=node.id,
            raw_data={},
            normalized={"name": node.name},
            metadata={"collector": node.source_int.lower()},
            reliability_grade="C",
        ))

    combined = combiner.combine_entity_evidence(entity_id, sources)

    return {
        "entity_id": entity_id,
        "evidence": combined.to_dict(),
        "neighbor_count": len(subgraph.nodes),
        "edge_count": len(subgraph.edges),
    }


@router.post("/correlate")
async def correlate_entities(
    entity_ids: list[str],
    window_hours: float = Query(24.0, description="Temporal window in hours"),
    max_distance_km: float = Query(50.0, description="Spatial distance threshold"),
    driver=Depends(get_neo4j),
):
    """Run cross-INT correlation on a set of entities."""
    client = Neo4jClient(driver)

    # Fetch entities by IDs
    records = await client.execute_read(
        """
        MATCH (e:Entity) WHERE e.id IN $ids
        RETURN e.id AS id, e.name AS name, e.type AS type,
               e.sourceInt AS source_int, e.firstSeen AS first_seen,
               e.coordinates AS coords
        """,
        {"ids": entity_ids},
    )

    entity_dicts = []
    for r in records:
        ent = {
            "id": r.get("id", ""),
            "name": r.get("name", ""),
            "source_int": r.get("source_int", ""),
            "first_seen": str(r.get("first_seen", "")) if r.get("first_seen") else None,
        }
        coords = r.get("coords")
        if coords:
            ent["location"] = {
                "latitude": coords.get("latitude"),
                "longitude": coords.get("longitude"),
            }
        entity_dicts.append(ent)

    correlator = CrossIntCorrelator()

    temporal = correlator.correlate_temporal(entity_dicts, window_hours=window_hours)
    spatial = correlator.correlate_spatial(entity_dicts, max_distance_km=max_distance_km)

    return {
        "temporal": [c.to_dict() for c in temporal],
        "spatial": [c.to_dict() for c in spatial],
        "total_correlations": len(temporal) + len(spatial),
    }
