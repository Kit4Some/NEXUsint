"""LLM-powered intelligence dossier generation for target entities."""

import json
from typing import Any

import httpx
import structlog

from nexus.config import settings
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.repository import EntityRepository
from nexus.knowledge.reasoning_engine import ReasoningEngine

logger = structlog.get_logger()

_DOSSIER_SYSTEM_PROMPT = """You are NEXUS, a professional intelligence analyst generating a target dossier.
Generate a structured intelligence briefing using the provided data. Be precise, cite confidence levels,
and reference entity identifiers.

Output format (markdown):

# Executive Summary
2-3 sentence overview: who/what is the target, key findings, assessed threat level.

# Key Identifiers
Table of all known identifiers (IPs, domains, accounts, aliases, MMSIs, callsigns).

# Network Analysis
Key connections and their significance. Community membership. Centrality assessment.

# Activity Timeline
Chronological summary of observed activity. First/last seen dates.

# Cross-INT Correlation
How this entity appears across intelligence types (CYBINT, SOCMINT, SIGINT, GEOINT).

# Risk Assessment
Risk score justification. Vulnerabilities, threat indicators, TTPs if applicable.

# Recommended Actions
Specific next collection steps, monitoring recommendations, investigation priorities."""


class DossierEngine:
    """Generate comprehensive intelligence dossiers for target entities."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client
        self._repo = EntityRepository(client)
        self._reasoning = ReasoningEngine(client)

    async def generate_dossier(self, entity_id: str) -> dict[str, Any]:
        """Generate a full intelligence dossier for an entity."""
        # 1. Gather all data
        entity = await self._repo.get_entity(entity_id)
        if not entity:
            return {"error": "Entity not found", "entity_id": entity_id}

        tracking = await self._reasoning.track_entity(entity_id)
        subgraph = await self._repo.get_subgraph(entity_id, depth=2)
        timeline = await self._repo.get_entity_timeline(entity_id)

        # Anomaly detection (optional, may fail)
        relevant_anomalies: list[Any] = []
        try:
            from nexus.analytics.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector(self._client)
            all_anomalies = await detector.detect_all(limit=50)
            relevant_anomalies = [
                a for a in all_anomalies if a.entity_id == entity_id
            ]
        except Exception:
            pass

        # 2. Build LLM context
        context = self._build_context(
            entity, tracking, subgraph, timeline, relevant_anomalies,
        )

        # 3. Call LLM
        dossier_markdown = await self._call_llm(context)

        # 4. Structure result
        return {
            "entity_id": entity_id,
            "entity_name": entity.name,
            "entity_type": entity.type.value,
            "dossier_markdown": dossier_markdown,
            "data": {
                "entity": {
                    "name": entity.name,
                    "type": entity.type.value,
                    "confidence": entity.confidence,
                    "risk_score": entity.risk_score,
                    "source_int": entity.source_int,
                    "first_seen": entity.first_seen.isoformat() if entity.first_seen else None,
                    "last_seen": entity.last_seen.isoformat() if entity.last_seen else None,
                    "properties": entity.properties,
                },
                "connection_count": len(subgraph.edges),
                "neighbor_count": len(subgraph.nodes) - 1 if subgraph.nodes else 0,
                "timeline_events": len(timeline),
                "anomaly_count": len(relevant_anomalies),
                "int_sources": tracking.get("intSourceBreakdown", {}),
                "location_trail": tracking.get("locationTrail", []),
            },
        }

    def _build_context(
        self, entity, tracking, subgraph, timeline, anomalies,
    ) -> str:
        parts: list[str] = []

        # Entity info
        parts.append("=== TARGET ENTITY ===")
        parts.append(f"Name: {entity.name}")
        parts.append(f"Type: {entity.type.value}")
        parts.append(f"Confidence: {entity.confidence:.0%}")
        parts.append(f"Risk Score: {entity.risk_score}/10")
        parts.append(f"Source INT: {entity.source_int}")
        if entity.first_seen:
            parts.append(f"First Seen: {entity.first_seen}")
        if entity.last_seen:
            parts.append(f"Last Seen: {entity.last_seen}")
        if entity.properties:
            parts.append(f"Properties: {json.dumps(entity.properties, default=str)[:800]}")

        # Network
        parts.append(f"\n=== NETWORK ({len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges) ===")
        for node in subgraph.nodes[:30]:
            parts.append(f"  [{node.type.value}] {node.name} (risk:{node.risk_score}/10, {node.source_int})")
        for edge in subgraph.edges[:30]:
            parts.append(f"  {edge.source_id} --[{edge.type}]--> {edge.target_id}")

        # Tracking chain
        parts.append(f"\n=== TRACKING DATA ===")
        parts.append(f"Total connections: {tracking.get('totalConnections', 0)}")
        parts.append(f"Location trail: {tracking.get('totalLocations', 0)} locations")
        parts.append(f"INT breakdown: {tracking.get('intSourceBreakdown', {})}")
        for loc in tracking.get("locationTrail", [])[:10]:
            parts.append(
                f"  Location: {loc.get('locationName')} "
                f"({loc.get('latitude')}, {loc.get('longitude')})"
            )

        # Timeline
        if timeline:
            parts.append(f"\n=== TIMELINE ({len(timeline)} events) ===")
            for evt in timeline[:20]:
                parts.append(f"  {evt.timestamp} | {evt.event_type} | {evt.title}")

        # Anomalies
        if anomalies:
            parts.append(f"\n=== ANOMALIES ===")
            for a in anomalies[:10]:
                parts.append(f"  [{a.anomaly_type}] score:{a.score:.2f} - {a.evidence}")

        return "\n".join(parts)

    async def _call_llm(self, context: str) -> str:
        """Call LLM to generate dossier markdown."""
        api_key = settings.openai_api_key
        if not api_key:
            return self._fallback_dossier(context)

        messages = [
            {"role": "system", "content": _DOSSIER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate an intelligence dossier:\n\n{context}"},
        ]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": settings.llm_model or "gpt-4o-mini",
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 4096,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.error("dossier.llm_failed", error=str(exc))
            return self._fallback_dossier(context)

    def _fallback_dossier(self, context: str) -> str:
        """Generate a structured dossier from raw data without LLM."""
        return (
            "# Intelligence Dossier (Auto-Generated)\n\n"
            "*LLM API key not configured. Showing raw intelligence data.*\n\n"
            "```\n"
            f"{context[:4000]}\n"
            "```\n\n"
            "*Configure OPENAI_API_KEY for AI-generated analysis.*"
        )
