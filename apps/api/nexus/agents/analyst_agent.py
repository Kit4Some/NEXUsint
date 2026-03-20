"""Analyst Agent — cross-INT correlation, graph analysis, pattern detection."""

from __future__ import annotations

from typing import Any

import structlog

from nexus.agents.state import NexusState
from nexus.api.websocket.handlers import emit_investigation_progress
from nexus.fusion.cross_int_correlator import CrossIntCorrelator

logger = structlog.get_logger()


async def analyst_agent(state: NexusState) -> dict[str, Any]:
    """Analyze extracted data: correlations, communities, centrality, patterns.

    Reads: resolved_entities, extracted_relationships, investigation_id
    Writes: correlations, communities, centrality_scores, patterns,
            risk_assessments, current_agent, status, progress, errors
    """
    investigation_id = state.get("investigation_id", "")
    resolved = state.get("resolved_entities", [])
    relationships = state.get("extracted_relationships", [])

    await emit_investigation_progress(
        investigation_id, "analyst", "running", 55, "Starting cross-INT analysis..."
    )

    errors: list[str] = list(state.get("errors", []))
    correlator = CrossIntCorrelator()

    # Build entity list for correlation
    entity_dicts = _build_entity_dicts(resolved)

    # Temporal correlation
    correlations: list[dict[str, Any]] = []
    try:
        temporal = correlator.correlate_temporal(entity_dicts)
        correlations.extend(c.to_dict() for c in temporal)
    except Exception as e:
        logger.warning("analyst_agent.temporal_failed", error=str(e))
        errors.append(f"Temporal correlation failed: {e}")

    # Spatial correlation
    try:
        spatial = correlator.correlate_spatial(entity_dicts)
        correlations.extend(c.to_dict() for c in spatial)
    except Exception as e:
        logger.warning("analyst_agent.spatial_failed", error=str(e))
        errors.append(f"Spatial correlation failed: {e}")

    await emit_investigation_progress(
        investigation_id,
        "analyst",
        "running",
        60,
        f"Found {len(correlations)} cross-INT correlations",
    )

    # Graph-based analysis (if Neo4j available)
    communities: list[dict[str, Any]] = []
    centrality: list[dict[str, Any]] = []
    try:
        communities, centrality = await _run_graph_analysis(resolved)
    except Exception as e:
        logger.warning("analyst_agent.graph_failed", error=str(e))
        errors.append(f"Graph analysis failed: {e}")

    await emit_investigation_progress(
        investigation_id, "analyst", "running", 65, "Detecting patterns..."
    )

    # Pattern detection
    patterns = _detect_patterns(resolved, relationships, correlations)

    # Risk assessment
    risk_assessments = _assess_risks(resolved, correlations, centrality)

    await emit_investigation_progress(
        investigation_id,
        "analyst",
        "completed",
        75,
        f"Analysis complete — {len(correlations)} correlations, "
        f"{len(patterns)} patterns, {len(risk_assessments)} risk items",
    )

    logger.info(
        "analyst_agent.done",
        investigation_id=investigation_id,
        correlations=len(correlations),
        communities=len(communities),
        patterns=len(patterns),
    )

    return {
        "correlations": correlations,
        "communities": communities,
        "centrality_scores": centrality,
        "patterns": patterns,
        "risk_assessments": risk_assessments,
        "current_agent": "verifier",
        "status": "verifying",
        "progress": 75,
        "errors": errors,
    }


def _build_entity_dicts(resolved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert resolved entities to dicts suitable for correlation."""
    entities = []
    for r in resolved:
        ent: dict[str, Any] = {
            "id": r.get("canonical_name", ""),
            "name": r.get("canonical_name", ""),
            "type": r.get("entity_type", ""),
        }
        # Extract source INT
        source_ints = r.get("source_ints", [])
        if source_ints:
            ent["source_int"] = source_ints[0] if isinstance(source_ints, list) else source_ints

        # Extract timestamps
        props = r.get("merged_properties", {})
        if "first_seen" in props:
            ent["first_seen"] = props["first_seen"]

        # Extract location if available
        if "latitude" in props and "longitude" in props:
            ent["location"] = {
                "latitude": props["latitude"],
                "longitude": props["longitude"],
            }

        entities.append(ent)
    return entities


async def _run_graph_analysis(
    resolved: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run graph algorithms if Neo4j is available."""
    try:
        from nexus.config import settings
        from nexus.knowledge.neo4j_client import Neo4jClient
        from nexus.knowledge.graph_algorithms import GraphAlgorithms

        client = Neo4jClient(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        ga = GraphAlgorithms(client)

        communities = await ga.run_louvain()
        centrality = await ga.run_pagerank()

        return communities, centrality
    except Exception:
        return [], []


def _detect_patterns(
    resolved: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    correlations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect notable patterns in the data."""
    patterns: list[dict[str, Any]] = []

    # Pattern 1: Entities with high cross-INT correlation
    cross_int_entities: dict[str, int] = {}
    for corr in correlations:
        for key in ("entity_a_id", "entity_b_id"):
            eid = corr.get(key, "")
            if eid:
                cross_int_entities[eid] = cross_int_entities.get(eid, 0) + 1

    for eid, count in cross_int_entities.items():
        if count >= 3:
            patterns.append({
                "type": "high_cross_int_activity",
                "entity_id": eid,
                "correlation_count": count,
                "description": f"Entity {eid} appears in {count} cross-INT correlations",
            })

    # Pattern 2: Relationship clusters
    rel_counts: dict[str, int] = {}
    for rel in relationships:
        src = rel.get("source_entity", "")
        if src:
            rel_counts[src] = rel_counts.get(src, 0) + 1

    for entity, count in rel_counts.items():
        if count >= 5:
            patterns.append({
                "type": "hub_entity",
                "entity_id": entity,
                "relationship_count": count,
                "description": f"Entity {entity} is a hub with {count} relationships",
            })

    # Pattern 3: Multi-source entities (corroborated)
    for r in resolved:
        source_ints = r.get("source_ints", [])
        if isinstance(source_ints, list) and len(source_ints) >= 3:
            patterns.append({
                "type": "multi_source_corroboration",
                "entity_id": r.get("canonical_name", ""),
                "source_count": len(source_ints),
                "description": f"Entity corroborated across {len(source_ints)} INT sources",
            })

    return patterns


def _assess_risks(
    resolved: list[dict[str, Any]],
    correlations: list[dict[str, Any]],
    centrality: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate risk assessments for entities."""
    assessments: list[dict[str, Any]] = []

    # Build centrality lookup
    centrality_map = {c.get("id", ""): c.get("score", 0) for c in centrality}

    for r in resolved:
        name = r.get("canonical_name", "")
        etype = r.get("entity_type", "")
        confidence = r.get("confidence", 0)

        # High-confidence threat indicators
        if etype in ("ThreatActor", "Malware", "Vulnerability") and confidence > 0.7:
            score = min(confidence * 1.2, 1.0)
            assessments.append({
                "entity_id": name,
                "entity_type": etype,
                "risk_score": round(score, 3),
                "factors": ["high_confidence_threat_indicator"],
                "recommendation": "Investigate immediately — high-confidence threat entity",
            })
        elif centrality_map.get(name, 0) > 0.5:
            assessments.append({
                "entity_id": name,
                "entity_type": etype,
                "risk_score": round(centrality_map[name], 3),
                "factors": ["high_centrality"],
                "recommendation": "Review — highly connected entity in the graph",
            })

    return assessments
