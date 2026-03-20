"""Ontology routes — n10s bridge, SHACL validation, RDF export, reasoning."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from nexus.dependencies import get_neo4j
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.ontology_bridge import OntologyBridge
from nexus.knowledge.shacl_validator import SHACLValidator
from nexus.knowledge.reasoning_engine import ReasoningEngine

router = APIRouter()


def _get_bridge(driver=Depends(get_neo4j)) -> OntologyBridge:
    return OntologyBridge(Neo4jClient(driver))


def _get_validator(driver=Depends(get_neo4j)) -> SHACLValidator:
    return SHACLValidator(Neo4jClient(driver))


def _get_reasoning(driver=Depends(get_neo4j)) -> ReasoningEngine:
    return ReasoningEngine(Neo4jClient(driver))


class ReasonRequest(BaseModel):
    entity_ids: list[str]
    reasoning_type: Literal["track", "correlate", "infer"]


@router.post("/initialize")
async def initialize_n10s(bridge: OntologyBridge = Depends(_get_bridge)) -> dict[str, str]:
    """Initialize n10s configuration in Neo4j."""
    await bridge.initialize_n10s()
    return {"status": "initialized"}


@router.post("/import")
async def import_ontology(
    bridge: OntologyBridge = Depends(_get_bridge),
) -> dict[str, Any]:
    """Import the NEXUS OWL ontology into Neo4j via n10s."""
    try:
        result = await bridge.import_ontology()
        return {"status": "imported", **result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")


@router.post("/import/rdf")
async def import_rdf(
    content: str,
    format: str = Query("Turtle"),
    bridge: OntologyBridge = Depends(_get_bridge),
) -> dict[str, Any]:
    """Import raw RDF content into Neo4j."""
    result = await bridge.import_rdf(content, format)
    return {"status": "imported", **result}


@router.get("/classes")
async def get_ontology_classes(
    bridge: OntologyBridge = Depends(_get_bridge),
) -> list[dict[str, Any]]:
    """Get all classes defined in the ontology."""
    return await bridge.get_ontology_classes()


@router.get("/properties")
async def get_ontology_properties(
    bridge: OntologyBridge = Depends(_get_bridge),
) -> list[dict[str, Any]]:
    """Get all properties defined in the ontology."""
    return await bridge.get_ontology_properties()


@router.get("/export/rdf")
async def export_subgraph_rdf(
    entity_id: str = Query(None, description="Entity ID to export"),
    depth: int = Query(1, ge=0, le=5),
    format: str = Query("Turtle"),
    bridge: OntologyBridge = Depends(_get_bridge),
) -> PlainTextResponse:
    """Export a subgraph as RDF in the specified format."""
    if entity_id:
        rdf = await bridge.export_entity_rdf(entity_id, depth)
    else:
        # Export all entities (limited)
        rdf = await bridge.export_subgraph_rdf(
            "MATCH (n) WHERE n.id IS NOT NULL RETURN n LIMIT 100"
        )

    content_type = "text/turtle" if format == "Turtle" else "application/rdf+xml"
    return PlainTextResponse(content=rdf, media_type=content_type)


@router.post("/validate")
async def validate_graph(
    entity_type: str = Query(None, description="Filter by entity type"),
    limit: int = Query(1000, ge=1, le=10000),
    validator: SHACLValidator = Depends(_get_validator),
) -> dict[str, Any]:
    """Run SHACL validation on graph data."""
    result = await validator.validate_all(entity_type, limit)
    return result.to_dict()


@router.post("/validate/{entity_id}")
async def validate_entity(
    entity_id: str,
    validator: SHACLValidator = Depends(_get_validator),
) -> dict[str, Any]:
    """Validate a specific entity against its ontology shape."""
    result = await validator.validate_entity(entity_id)
    return result.to_dict()


@router.post("/validate/relationships")
async def validate_relationships(
    validator: SHACLValidator = Depends(_get_validator),
) -> dict[str, Any]:
    """Validate relationship domain/range constraints."""
    result = await validator.validate_relationships()
    return result.to_dict()


@router.get("/search")
async def ontology_search(
    class_name: str = Query(..., description="Ontology class name (e.g. Person, IPAddress)"),
    bridge: OntologyBridge = Depends(_get_bridge),
) -> list[dict[str, Any]]:
    """Search entities using ontology class hierarchy (including subclasses)."""
    return await bridge.ontology_aware_search(class_name)


# --- Reasoning & Tracking Endpoints ---


@router.get("/tracking/{entity_id}")
async def get_tracking(
    entity_id: str,
    engine: ReasoningEngine = Depends(_get_reasoning),
) -> dict[str, Any]:
    """Build a temporal tracking chain for an entity.

    Returns direct relationships, location trail, extended network,
    and cross-INT source breakdown.
    """
    result = await engine.track_entity(entity_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/reason")
async def reason(
    req: ReasonRequest,
    engine: ReasoningEngine = Depends(_get_reasoning),
) -> dict[str, Any]:
    """Run ontology-based reasoning over entities.

    reasoning_type:
    - track: temporal tracking chain for the first entity
    - correlate: find shared neighbors, paths, and cross-INT links
    - infer: ontology rule-based inference of implicit relationships
    """
    try:
        if req.reasoning_type == "track":
            return await engine.track_entity(req.entity_ids[0])
        elif req.reasoning_type == "correlate":
            return await engine.correlate_entities(req.entity_ids)
        elif req.reasoning_type == "infer":
            return await engine.infer_relationships(req.entity_ids[0])
        else:
            raise HTTPException(status_code=400, detail=f"Unknown reasoning type: {req.reasoning_type}")
    except IndexError:
        raise HTTPException(status_code=400, detail="At least one entity_id is required")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reasoning failed: {e}")
