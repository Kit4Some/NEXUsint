"""STIX 2.1 Bundle generation and parsing."""

from typing import Any
from uuid import uuid4

import structlog

from nexus.interop.stix_converter import STIXConverter

logger = structlog.get_logger()


class STIXBundleBuilder:
    """Builds STIX 2.1 Bundles from NEXUS investigation data."""

    def __init__(self) -> None:
        self._converter = STIXConverter()

    def build_bundle(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build a complete STIX 2.1 Bundle from entities + relationships."""
        objects: list[dict[str, Any]] = []
        id_map: dict[str, str] = {}  # nexus_id -> stix_id

        # Convert entities to SDOs
        for entity in entities:
            sdo = self._converter.entity_to_sdo(entity)
            if sdo:
                objects.append(sdo)
                nexus_id = entity.get("id", "")
                id_map[nexus_id] = sdo["id"]

        # Convert relationships to SROs
        for rel in relationships:
            source_id = rel.get("source_id", rel.get("source", ""))
            target_id = rel.get("target_id", rel.get("target", ""))

            source_stix_id = id_map.get(source_id)
            target_stix_id = id_map.get(target_id)

            if not source_stix_id or not target_stix_id:
                logger.debug(
                    "stix.missing_entity_for_rel",
                    source_id=source_id,
                    target_id=target_id,
                )
                continue

            sro = self._converter.relationship_to_sro(rel, source_stix_id, target_stix_id)
            if sro:
                objects.append(sro)

        bundle: dict[str, Any] = {
            "type": "bundle",
            "id": f"bundle--{uuid4()}",
            "spec_version": "2.1",
            "objects": objects,
        }

        logger.info(
            "stix.bundle_built",
            sdo_count=sum(1 for o in objects if o["type"] != "relationship"),
            sro_count=sum(1 for o in objects if o["type"] == "relationship"),
        )
        return bundle

    def build_investigation_bundle(
        self,
        investigation_id: str,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        report_summary: str | None = None,
    ) -> dict[str, Any]:
        """Build a STIX Bundle for an entire investigation, with optional Report SDO."""
        bundle = self.build_bundle(entities, relationships)

        if report_summary:
            # Add a STIX Report SDO referencing all objects
            object_refs = [obj["id"] for obj in bundle["objects"]]
            report_sdo: dict[str, Any] = {
                "type": "report",
                "spec_version": "2.1",
                "id": f"report--{uuid4()}",
                "name": f"NEXUS Investigation {investigation_id}",
                "description": report_summary,
                "published": bundle["objects"][0].get("created", "") if bundle["objects"] else "",
                "report_types": ["threat-report"],
                "object_refs": object_refs,
                "x_nexus_investigation_id": investigation_id,
            }
            bundle["objects"].append(report_sdo)

        return bundle


class STIXBundleImporter:
    """Imports STIX 2.1 Bundles into NEXUS."""

    def __init__(self) -> None:
        self._converter = STIXConverter()

    def parse_bundle(
        self,
        bundle: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Parse a STIX Bundle into NEXUS entities and relationships."""
        objects = bundle.get("objects", [])
        entities: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        # First pass: build STIX ID -> NEXUS entity map
        id_map: dict[str, str] = {}

        for obj in objects:
            obj_type = obj.get("type", "")

            if obj_type == "relationship":
                continue  # Handle in second pass
            elif obj_type == "bundle":
                continue
            elif obj_type == "report":
                continue  # Reports are metadata, not entities

            entity = self._converter.sdo_to_entity(obj)
            entities.append(entity)
            id_map[obj["id"]] = entity["id"]

        # Second pass: convert relationships
        for obj in objects:
            if obj.get("type") == "relationship":
                rel = self._converter.sro_to_relationship(obj, id_map)
                relationships.append(rel)

        logger.info(
            "stix.bundle_parsed",
            entity_count=len(entities),
            relationship_count=len(relationships),
        )
        return entities, relationships

    async def import_bundle(
        self,
        bundle: dict[str, Any],
        entity_repo: Any,
    ) -> dict[str, Any]:
        """Import a STIX Bundle, creating entities and relationships in Neo4j."""
        entities, relationships = self.parse_bundle(bundle)
        created_entities = 0
        created_rels = 0
        errors: list[str] = []

        for entity in entities:
            try:
                await entity_repo.create_entity(
                    entity_type=entity["type"],
                    entity_id=entity["id"],
                    name=entity["name"],
                    confidence=entity.get("confidence", 0.5),
                    source_int=entity.get("sourceInt", "STIX_IMPORT"),
                    risk_score=entity.get("riskScore", 0.0),
                    properties=entity.get("properties", {}),
                )
                created_entities += 1
            except Exception as e:
                errors.append(f"Entity {entity['id']}: {e}")
                logger.error("stix.import_entity_failed", entity_id=entity["id"], error=str(e))

        for rel in relationships:
            try:
                await entity_repo.create_relationship(
                    source_id=rel["source_id"],
                    target_id=rel["target_id"],
                    relationship_type=rel["type"],
                    confidence=rel.get("confidence", 0.5),
                    properties=rel.get("properties", {}),
                )
                created_rels += 1
            except Exception as e:
                errors.append(f"Rel {rel['source_id']}->{rel['target_id']}: {e}")
                logger.error("stix.import_rel_failed", error=str(e))

        return {
            "entities_created": created_entities,
            "relationships_created": created_rels,
            "errors": errors,
        }
