"""Ontology-based reasoning engine for high-dimensional OSINT analysis.

Provides entity tracking, cross-INT correlation, and inference
over the Neo4j knowledge graph using ontological relationships.
"""

from typing import Any

import structlog

from nexus.knowledge.neo4j_client import Neo4jClient

logger = structlog.get_logger()


def _safe_str(value: Any) -> str | None:
    """Convert Neo4j values (DateTime, etc.) to JSON-safe strings."""
    if value is None:
        return None
    return str(value)


class ReasoningEngine:
    """High-level reasoning over the OSINT knowledge graph."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    async def track_entity(self, entity_id: str) -> dict[str, Any]:
        """Build a temporal tracking chain for an entity.

        Multi-hop traversal collecting:
        - Direct relationships with timestamps
        - Associated locations (geographic trail)
        - Communication patterns
        - Attribution chains
        """
        try:
            return await self._track_entity_impl(entity_id)
        except Exception as exc:
            logger.error("reasoning.track_entity_failed", entity_id=entity_id, error=str(exc))
            return {"error": f"Tracking failed: {exc}", "entity_id": entity_id}

    async def _track_entity_impl(self, entity_id: str) -> dict[str, Any]:
        # 1. Get the entity itself
        entity_q = """
        MATCH (e:Entity {id: $id})
        RETURN e.id AS id, e.name AS name, e.type AS type,
               e.sourceInt AS sourceInt, e.confidence AS confidence,
               e.riskScore AS riskScore,
               e.firstSeen AS firstSeen, e.lastSeen AS lastSeen
        """
        records = await self._client.execute_read(entity_q, {"id": entity_id})
        if not records:
            return {"error": "Entity not found", "entity_id": entity_id}

        r0 = records[0]
        entity = {
            "id": r0["id"], "name": r0["name"], "type": r0["type"],
            "sourceInt": r0.get("sourceInt"), "confidence": r0.get("confidence"),
            "riskScore": r0.get("riskScore"),
            "firstSeen": _safe_str(r0.get("firstSeen")),
            "lastSeen": _safe_str(r0.get("lastSeen")),
        }

        # 2. Get all direct relationships (2-hop) with temporal data
        rel_q = """
        MATCH (e:Entity {id: $id})-[r]-(neighbor:Entity)
        RETURN neighbor.id AS neighborId, neighbor.name AS neighborName,
               neighbor.type AS neighborType, neighbor.sourceInt AS neighborSourceInt,
               neighbor.confidence AS neighborConfidence,
               type(r) AS relType, r.confidence AS relConfidence,
               r.firstSeen AS relFirstSeen, r.lastSeen AS relLastSeen,
               startNode(r) = e AS isOutgoing
        ORDER BY r.firstSeen ASC
        """
        rel_records = await self._client.execute_read(rel_q, {"id": entity_id})

        relationships = []
        for r in rel_records:
            relationships.append({
                "neighborId": r["neighborId"],
                "neighborName": r["neighborName"],
                "neighborType": r["neighborType"],
                "neighborSourceInt": r["neighborSourceInt"],
                "relType": r["relType"],
                "relConfidence": r.get("relConfidence"),
                "relFirstSeen": _safe_str(r.get("relFirstSeen")),
                "relLastSeen": _safe_str(r.get("relLastSeen")),
                "direction": "outgoing" if r["isOutgoing"] else "incoming",
            })

        # 3. Location trail — all LOCATED_AT relationships ordered by time
        loc_q = """
        MATCH (e:Entity {id: $id})-[r:LOCATED_AT]->(loc:Entity)
        RETURN loc.id AS locationId, loc.name AS locationName,
               loc.coordinates AS coordinates,
               r.firstSeen AS firstSeen, r.lastSeen AS lastSeen
        ORDER BY r.firstSeen ASC
        """
        loc_records = await self._client.execute_read(loc_q, {"id": entity_id})

        location_trail = []
        for r in loc_records:
            coords = r.get("coordinates")
            lat, lon = None, None
            if coords:
                lat = getattr(coords, "latitude", None) or (coords.get("latitude") if isinstance(coords, dict) else None)
                lon = getattr(coords, "longitude", None) or (coords.get("longitude") if isinstance(coords, dict) else None)
            location_trail.append({
                "locationId": r["locationId"],
                "locationName": r["locationName"],
                "latitude": lat,
                "longitude": lon,
                "firstSeen": _safe_str(r.get("firstSeen")),
                "lastSeen": _safe_str(r.get("lastSeen")),
            })

        # 4. Communication/association chain — 2-hop
        chain_q = """
        MATCH path = (e:Entity {id: $id})-[r1]-(mid:Entity)-[r2]-(far:Entity)
        WHERE far.id <> e.id
        RETURN mid.id AS midId, mid.name AS midName, mid.type AS midType,
               type(r1) AS rel1, type(r2) AS rel2,
               far.id AS farId, far.name AS farName, far.type AS farType,
               far.sourceInt AS farSourceInt
        LIMIT 30
        """
        chain_records = await self._client.execute_read(chain_q, {"id": entity_id})

        extended_network = []
        seen = set()
        for r in chain_records:
            key = f"{r['midId']}-{r['farId']}"
            if key in seen:
                continue
            seen.add(key)
            extended_network.append({
                "via": {"id": r["midId"], "name": r["midName"], "type": r["midType"], "rel": r["rel1"]},
                "target": {"id": r["farId"], "name": r["farName"], "type": r["farType"], "rel": r["rel2"]},
                "targetSourceInt": r["farSourceInt"],
            })

        # 5. INT source breakdown
        int_sources = {}
        for rel in relationships:
            src = rel.get("neighborSourceInt", "UNKNOWN")
            int_sources[src] = int_sources.get(src, 0) + 1

        return {
            "entity": entity,
            "relationships": relationships,
            "locationTrail": location_trail,
            "extendedNetwork": extended_network[:20],
            "intSourceBreakdown": int_sources,
            "totalConnections": len(relationships),
            "totalLocations": len(location_trail),
        }

    async def correlate_entities(self, entity_ids: list[str]) -> dict[str, Any]:
        """Find correlations between a set of entities.

        Looks for:
        - Shared neighbors (common connections)
        - Temporal overlap (active in same time windows)
        - Geographic proximity
        - Cross-INT linkages
        """
        if len(entity_ids) < 2:
            return {"error": "Need at least 2 entity IDs", "correlations": []}

        # 1. Shared neighbors
        shared_q = """
        UNWIND $ids AS eid
        MATCH (e:Entity {id: eid})-[r]-(neighbor:Entity)
        WHERE NOT neighbor.id IN $ids
        WITH neighbor, collect(DISTINCT e.id) AS connectedFrom, count(r) AS relCount
        WHERE size(connectedFrom) >= 2
        RETURN neighbor.id AS neighborId, neighbor.name AS neighborName,
               neighbor.type AS neighborType, connectedFrom, relCount
        ORDER BY size(connectedFrom) DESC, relCount DESC
        LIMIT 20
        """
        shared_records = await self._client.execute_read(shared_q, {"ids": entity_ids})

        shared_neighbors = []
        for r in shared_records:
            shared_neighbors.append({
                "neighborId": r["neighborId"],
                "neighborName": r["neighborName"],
                "neighborType": r["neighborType"],
                "connectedFrom": r["connectedFrom"],
                "relationshipCount": r["relCount"],
            })

        # 2. Direct paths between the entities
        paths = []
        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                path_q = """
                MATCH path = shortestPath((a:Entity {id: $from})-[*..4]-(b:Entity {id: $to}))
                RETURN [n IN nodes(path) | {id: n.id, name: n.name, type: n.type}] AS nodes,
                       [r IN relationships(path) | type(r)] AS relTypes,
                       length(path) AS pathLength
                """
                path_records = await self._client.execute_read(
                    path_q, {"from": entity_ids[i], "to": entity_ids[j]}
                )
                if path_records:
                    p = path_records[0]
                    paths.append({
                        "from": entity_ids[i],
                        "to": entity_ids[j],
                        "nodes": p["nodes"],
                        "relTypes": p["relTypes"],
                        "pathLength": p["pathLength"],
                    })

        # 3. Cross-INT analysis
        crossint_q = """
        UNWIND $ids AS eid
        MATCH (e:Entity {id: eid})
        RETURN e.id AS id, e.sourceInt AS sourceInt, e.type AS type, e.name AS name
        """
        crossint_records = await self._client.execute_read(crossint_q, {"ids": entity_ids})
        source_map: dict[str, list[dict]] = {}
        for r in crossint_records:
            src = r.get("sourceInt", "UNKNOWN")
            source_map.setdefault(src, []).append({"id": r["id"], "name": r["name"], "type": r["type"]})

        return {
            "entityCount": len(entity_ids),
            "sharedNeighbors": shared_neighbors,
            "paths": paths,
            "crossIntAnalysis": {
                "sourceBreakdown": {k: len(v) for k, v in source_map.items()},
                "entitiesBySource": source_map,
                "isCrossInt": len(source_map) > 1,
            },
        }

    async def infer_relationships(self, entity_id: str) -> dict[str, Any]:
        """Ontology-based inference of implicit relationships.

        Rules:
        - A -[PART_OF]-> B -[TARGETS]-> C  ⇒  A indirectly targets C
        - A -[ATTRIBUTED_TO]-> B -[USES]-> C  ⇒  A likely uses C
        - A -[COMMUNICATES_WITH]-> B -[LOCATED_AT]-> L  ⇒  A has geographic link to L
        - A -[RESOLVES_TO]-> IP -[HOSTS]-> D  ⇒  A is infrastructure-linked to D
        """
        inferences = []

        # Rule 1: Indirect targeting via PART_OF
        r1_q = """
        MATCH (e:Entity {id: $id})-[:PART_OF]->(group)-[:TARGETS]->(target)
        WHERE NOT (e)-[:TARGETS]->(target)
        RETURN 'indirect_targets' AS rule,
               group.id AS viaId, group.name AS viaName, group.type AS viaType,
               target.id AS targetId, target.name AS targetName, target.type AS targetType,
               'PART_OF → TARGETS' AS chain
        """
        r1 = await self._client.execute_read(r1_q, {"id": entity_id})
        for r in r1:
            inferences.append({
                "rule": r["rule"],
                "chain": r["chain"],
                "via": {"id": r["viaId"], "name": r["viaName"], "type": r["viaType"]},
                "inferred": {"id": r["targetId"], "name": r["targetName"], "type": r["targetType"]},
                "confidence": 0.7,
            })

        # Rule 2: Tool/malware usage via ATTRIBUTED_TO
        r2_q = """
        MATCH (e:Entity {id: $id})-[:ATTRIBUTED_TO]->(actor)-[:USES]->(tool)
        WHERE NOT (e)-[:USES]->(tool)
        RETURN 'likely_uses' AS rule,
               actor.id AS viaId, actor.name AS viaName, actor.type AS viaType,
               tool.id AS targetId, tool.name AS targetName, tool.type AS targetType,
               'ATTRIBUTED_TO → USES' AS chain
        """
        r2 = await self._client.execute_read(r2_q, {"id": entity_id})
        for r in r2:
            inferences.append({
                "rule": r["rule"],
                "chain": r["chain"],
                "via": {"id": r["viaId"], "name": r["viaName"], "type": r["viaType"]},
                "inferred": {"id": r["targetId"], "name": r["targetName"], "type": r["targetType"]},
                "confidence": 0.6,
            })

        # Rule 3: Geographic link via communication
        r3_q = """
        MATCH (e:Entity {id: $id})-[:COMMUNICATES_WITH]->(peer)-[:LOCATED_AT]->(loc)
        WHERE NOT (e)-[:LOCATED_AT]->(loc)
        RETURN 'geographic_link' AS rule,
               peer.id AS viaId, peer.name AS viaName, peer.type AS viaType,
               loc.id AS targetId, loc.name AS targetName, loc.type AS targetType,
               'COMMUNICATES_WITH → LOCATED_AT' AS chain
        """
        r3 = await self._client.execute_read(r3_q, {"id": entity_id})
        for r in r3:
            inferences.append({
                "rule": r["rule"],
                "chain": r["chain"],
                "via": {"id": r["viaId"], "name": r["viaName"], "type": r["viaType"]},
                "inferred": {"id": r["targetId"], "name": r["targetName"], "type": r["targetType"]},
                "confidence": 0.5,
            })

        # Rule 4: Infrastructure linkage via DNS resolution
        r4_q = """
        MATCH (e:Entity {id: $id})-[:RESOLVES_TO]->(ip)-[:HOSTS]->(service)
        WHERE NOT (e)-[:HOSTS]->(service)
        RETURN 'infra_linked' AS rule,
               ip.id AS viaId, ip.name AS viaName, ip.type AS viaType,
               service.id AS targetId, service.name AS targetName, service.type AS targetType,
               'RESOLVES_TO → HOSTS' AS chain
        """
        r4 = await self._client.execute_read(r4_q, {"id": entity_id})
        for r in r4:
            inferences.append({
                "rule": r["rule"],
                "chain": r["chain"],
                "via": {"id": r["viaId"], "name": r["viaName"], "type": r["viaType"]},
                "inferred": {"id": r["targetId"], "name": r["targetName"], "type": r["targetType"]},
                "confidence": 0.8,
            })

        # Deduplicate by target
        seen_targets = set()
        unique_inferences = []
        for inf in inferences:
            tid = inf["inferred"]["id"]
            if tid not in seen_targets:
                seen_targets.add(tid)
                unique_inferences.append(inf)

        return {
            "entityId": entity_id,
            "inferences": unique_inferences,
            "totalInferred": len(unique_inferences),
            "rules_applied": ["indirect_targets", "likely_uses", "geographic_link", "infra_linked"],
        }
