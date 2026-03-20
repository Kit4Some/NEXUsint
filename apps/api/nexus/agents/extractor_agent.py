"""Extractor Agent — runs NER, relation extraction, entity resolution."""

from __future__ import annotations

from typing import Any

import structlog

from nexus.agents.state import NexusState
from nexus.api.websocket.handlers import emit_investigation_progress, emit_new_entity
from nexus.processing.ner import NERPipeline
from nexus.processing.relation_extraction import RelationExtractor
from nexus.processing.entity_resolution import EntityResolver

logger = structlog.get_logger()


async def extractor_agent(state: NexusState) -> dict[str, Any]:
    """Extract entities, relationships, and resolve duplicates.

    Reads: collection_results, investigation_id
    Writes: extracted_entities, extracted_relationships, resolved_entities,
            current_agent, status, progress, errors
    """
    investigation_id = state.get("investigation_id", "")
    collection_results = state.get("collection_results", [])

    await emit_investigation_progress(
        investigation_id, "extractor", "running", 30, "Starting NER pipeline..."
    )

    errors: list[str] = list(state.get("errors", []))
    ner = NERPipeline()
    re_extractor = RelationExtractor()
    resolver = EntityResolver()

    all_entities = []
    all_relations = []

    # Process each collection result through NER + RE
    for i, result in enumerate(collection_results):
        try:
            # Build text from normalized data for NER
            normalized = result.get("normalized", {})
            raw_data = result.get("raw_data", {})
            source_int = result.get("source_int", "")

            text = _build_text_from_result(normalized, raw_data)
            if not text:
                continue

            # NER
            entities = ner.extract(text)
            for ent in entities:
                ent.source = source_int

            all_entities.extend(entities)

            # Relation extraction
            relations = await re_extractor.extract(text, entities, source=source_int)
            all_relations.extend(relations)

        except Exception as e:
            logger.warning("extractor_agent.result_failed", index=i, error=str(e))
            errors.append(f"Extraction failed for result {i}: {e}")

        # Progress updates every 10 results
        if (i + 1) % 10 == 0 or i == len(collection_results) - 1:
            pct = 30 + int(15 * (i + 1) / max(len(collection_results), 1))
            await emit_investigation_progress(
                investigation_id,
                "extractor",
                "running",
                pct,
                f"Processed {i + 1}/{len(collection_results)} results — "
                f"{len(all_entities)} entities, {len(all_relations)} relations",
            )

    # Entity resolution
    await emit_investigation_progress(
        investigation_id, "extractor", "running", 45, "Resolving entities..."
    )

    resolved = resolver.resolve(all_entities)

    # Emit new entities via WebSocket
    for re_ent in resolved[:50]:  # Limit WebSocket emissions
        await emit_new_entity(re_ent.to_dict())

    await emit_investigation_progress(
        investigation_id,
        "extractor",
        "completed",
        50,
        f"Extraction complete — {len(resolved)} resolved entities, {len(all_relations)} relations",
    )

    logger.info(
        "extractor_agent.done",
        investigation_id=investigation_id,
        raw_entities=len(all_entities),
        resolved_entities=len(resolved),
        relations=len(all_relations),
    )

    return {
        "extracted_entities": [e.to_dict() for e in all_entities],
        "extracted_relationships": [r.to_dict() for r in all_relations],
        "resolved_entities": [r.to_dict() for r in resolved],
        "current_agent": "analyst",
        "status": "analyzing",
        "progress": 50,
        "errors": errors,
    }


def _build_text_from_result(normalized: dict, raw_data: dict) -> str:
    """Build a text string from collection result for NER processing."""
    parts = []

    # Add name/title
    for key in ("name", "title", "hostname", "domain", "callsign", "vessel_name"):
        val = normalized.get(key) or raw_data.get(key)
        if val:
            parts.append(str(val))

    # Add description/content
    for key in ("description", "content", "text", "body", "bio"):
        val = normalized.get(key) or raw_data.get(key)
        if val:
            parts.append(str(val))

    # Add tags/labels
    tags = normalized.get("tags") or raw_data.get("tags") or []
    if isinstance(tags, list):
        parts.append(" ".join(str(t) for t in tags))

    # Add IP/domains
    for key in ("ip", "ip_str", "domains", "hostnames"):
        val = normalized.get(key) or raw_data.get(key)
        if val:
            if isinstance(val, list):
                parts.extend(str(v) for v in val)
            else:
                parts.append(str(val))

    return " ".join(parts)
