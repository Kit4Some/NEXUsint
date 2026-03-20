"""STIX 2.1 import/export routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from nexus.dependencies import get_neo4j
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.repository import EntityRepository
from nexus.interop.stix_bundle import STIXBundleBuilder, STIXBundleImporter
from nexus.api.middleware.rbac import require_viewer, require_analyst

router = APIRouter()

_builder = STIXBundleBuilder()
_importer = STIXBundleImporter()


@router.get("/export/investigation/{investigation_id}")
async def export_investigation_stix(
    investigation_id: str,
    _user=Depends(require_viewer),
    driver=Depends(get_neo4j),
) -> dict[str, Any]:
    """Export an investigation's entities and relationships as a STIX 2.1 Bundle."""
    client = Neo4jClient(driver)
    repo = EntityRepository(client)

    # Fetch all entities linked to the investigation
    entities = await client.execute_read(
        """
        MATCH (e)
        WHERE e.investigationId = $invId OR e.id IS NOT NULL
        RETURN e {.*, type: head(labels(e))} AS entity
        LIMIT 500
        """,
        {"invId": investigation_id},
    )

    relationships = await client.execute_read(
        """
        MATCH (a)-[r]->(b)
        WHERE a.investigationId = $invId OR b.investigationId = $invId
           OR (a.id IS NOT NULL AND b.id IS NOT NULL)
        RETURN a.id AS source_id, b.id AS target_id,
               type(r) AS type, r.confidence AS confidence
        LIMIT 1000
        """,
        {"invId": investigation_id},
    )

    entity_list = [e["entity"] for e in entities if e.get("entity")]
    rel_list = [dict(r) for r in relationships]

    bundle = _builder.build_investigation_bundle(
        investigation_id=investigation_id,
        entities=entity_list,
        relationships=rel_list,
        report_summary=f"NEXUS investigation {investigation_id}",
    )

    return bundle


@router.get("/export/entity/{entity_id}")
async def export_entity_stix(
    entity_id: str,
    depth: int = Query(1, ge=0, le=3),
    _user=Depends(require_viewer),
    driver=Depends(get_neo4j),
) -> dict[str, Any]:
    """Export an entity and its subgraph as a STIX 2.1 Bundle."""
    client = Neo4jClient(driver)

    entities = await client.execute_read(
        """
        MATCH path = (e {id: $entityId})-[*0..$depth]-(n)
        WITH COLLECT(DISTINCT e) + COLLECT(DISTINCT n) AS nodes
        UNWIND nodes AS node
        RETURN DISTINCT node {.*, type: head(labels(node))} AS entity
        """,
        {"entityId": entity_id, "depth": depth},
    )

    relationships = await client.execute_read(
        """
        MATCH (e {id: $entityId})-[*0..$depth]-(n)
        WITH COLLECT(DISTINCT e) + COLLECT(DISTINCT n) AS nodes
        UNWIND nodes AS a
        MATCH (a)-[r]->(b)
        WHERE b IN nodes
        RETURN a.id AS source_id, b.id AS target_id,
               type(r) AS type, r.confidence AS confidence
        """,
        {"entityId": entity_id, "depth": depth},
    )

    if not entities:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity_list = [e["entity"] for e in entities if e.get("entity")]
    rel_list = [dict(r) for r in relationships]

    bundle = _builder.build_bundle(entity_list, rel_list)
    return bundle


@router.post("/import")
async def import_stix_bundle(
    bundle: dict[str, Any],
    _user=Depends(require_analyst),
    driver=Depends(get_neo4j),
) -> dict[str, Any]:
    """Import a STIX 2.1 Bundle into the NEXUS knowledge graph."""
    # Validate bundle structure
    if bundle.get("type") != "bundle":
        raise HTTPException(status_code=400, detail="Invalid STIX bundle: type must be 'bundle'")
    if bundle.get("spec_version") not in ("2.1", "2.0"):
        raise HTTPException(status_code=400, detail="Unsupported STIX version")
    if not bundle.get("objects"):
        raise HTTPException(status_code=400, detail="Bundle contains no objects")

    client = Neo4jClient(driver)
    repo = EntityRepository(client)

    result = await _importer.import_bundle(bundle, repo)
    return result


@router.post("/validate")
async def validate_stix_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Validate a STIX 2.1 Bundle structure without importing."""
    errors: list[str] = []

    if bundle.get("type") != "bundle":
        errors.append("Missing or invalid 'type' field (expected 'bundle')")

    if bundle.get("spec_version") not in ("2.1", "2.0"):
        errors.append(f"Unsupported spec_version: {bundle.get('spec_version')}")

    if not bundle.get("id", "").startswith("bundle--"):
        errors.append("Invalid bundle ID format (expected 'bundle--<uuid>')")

    objects = bundle.get("objects", [])
    if not objects:
        errors.append("Bundle contains no objects")

    for i, obj in enumerate(objects):
        if "type" not in obj:
            errors.append(f"Object {i}: missing 'type' field")
        if "id" not in obj:
            errors.append(f"Object {i}: missing 'id' field")
        if obj.get("type") == "relationship":
            if "source_ref" not in obj:
                errors.append(f"Object {i}: relationship missing 'source_ref'")
            if "target_ref" not in obj:
                errors.append(f"Object {i}: relationship missing 'target_ref'")

    return {
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "errors": errors,
        "object_count": len(objects),
    }
