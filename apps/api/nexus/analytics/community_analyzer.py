"""Enhanced community analysis with INT composition and cross-community bridges."""

from typing import Any
from collections import Counter

import structlog

from nexus.knowledge.neo4j_client import Neo4jClient

logger = structlog.get_logger()


class CommunityAnalyzer:
    """Advanced community detection and analysis."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    async def detect_communities_enhanced(self) -> dict[str, Any]:
        """Run Louvain community detection with enriched metadata."""
        results = await self._client.execute_read(
            """
            CALL gds.louvain.stream('entity-graph')
            YIELD nodeId, communityId
            WITH gds.util.asNode(nodeId) AS node, communityId
            RETURN node.id AS id,
                   node.name AS name,
                   head(labels(node)) AS type,
                   node.sourceInt AS source_int,
                   coalesce(node.confidence, 0.5) AS confidence,
                   coalesce(node.riskScore, 0.0) AS risk_score,
                   communityId
            """,
            {},
        )

        if not results:
            return {"communities": [], "community_count": 0, "bridges": []}

        # Group by community
        communities: dict[int, list[dict[str, Any]]] = {}
        for r in results:
            cid = r["communityId"]
            if cid not in communities:
                communities[cid] = []
            communities[cid].append({
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "source_int": r["source_int"],
                "confidence": r["confidence"],
                "risk_score": r["risk_score"],
            })

        # Enrich each community
        enriched = []
        for cid, members in communities.items():
            int_counts = Counter(m.get("source_int", "UNKNOWN") for m in members)
            type_counts = Counter(m.get("type", "Unknown") for m in members)
            avg_confidence = sum(m["confidence"] for m in members) / len(members)
            avg_risk = sum(m["risk_score"] for m in members) / len(members)
            max_risk = max(m["risk_score"] for m in members)

            enriched.append({
                "community_id": cid,
                "member_count": len(members),
                "members": members[:50],  # Cap for large communities
                "int_composition": dict(int_counts),
                "type_composition": dict(type_counts),
                "average_confidence": round(avg_confidence, 3),
                "average_risk": round(avg_risk, 2),
                "max_risk": round(max_risk, 2),
                "risk_level": (
                    "critical" if max_risk >= 9.0
                    else "high" if max_risk >= 7.0
                    else "medium" if max_risk >= 4.0
                    else "low"
                ),
            })

        enriched.sort(key=lambda c: c["member_count"], reverse=True)

        logger.info("analytics.communities_detected", count=len(enriched))
        return {
            "communities": enriched,
            "community_count": len(enriched),
        }

    async def get_community_details(self, community_id: int) -> dict[str, Any]:
        """Get detailed info for a specific community."""
        results = await self._client.execute_read(
            """
            CALL gds.louvain.stream('entity-graph')
            YIELD nodeId, communityId
            WHERE communityId = $cid
            WITH gds.util.asNode(nodeId) AS node
            RETURN node.id AS id,
                   node.name AS name,
                   head(labels(node)) AS type,
                   node.sourceInt AS source_int,
                   coalesce(node.confidence, 0.5) AS confidence,
                   coalesce(node.riskScore, 0.0) AS risk_score
            """,
            {"cid": community_id},
        )

        members = [dict(r) for r in results]

        # Get internal relationships
        member_ids = [m["id"] for m in members]
        rels = await self._client.execute_read(
            """
            MATCH (a)-[r]->(b)
            WHERE a.id IN $ids AND b.id IN $ids
            RETURN a.id AS source, b.id AS target,
                   type(r) AS type, r.confidence AS confidence
            """,
            {"ids": member_ids},
        )

        int_counts = Counter(m.get("source_int", "UNKNOWN") for m in members)
        density = (
            (2 * len(rels)) / (len(members) * (len(members) - 1))
            if len(members) > 1 else 0.0
        )

        return {
            "community_id": community_id,
            "member_count": len(members),
            "members": members,
            "internal_relationships": [dict(r) for r in rels],
            "internal_density": round(density, 4),
            "int_composition": dict(int_counts),
        }

    async def find_cross_community_bridges(self) -> list[dict[str, Any]]:
        """Find entities that connect different communities."""
        results = await self._client.execute_read(
            """
            CALL gds.louvain.stream('entity-graph')
            YIELD nodeId, communityId
            WITH gds.util.asNode(nodeId) AS node, communityId
            WITH node, communityId
            MATCH (node)-[r]-(neighbor)
            CALL gds.louvain.stream('entity-graph')
            YIELD nodeId AS nId, communityId AS nCommunity
            WITH node, communityId, neighbor, nCommunity
            WHERE id(neighbor) = nId AND communityId <> nCommunity
            WITH node.id AS id, node.name AS name,
                 communityId AS home_community,
                 collect(DISTINCT nCommunity) AS connected_communities,
                 count(DISTINCT nCommunity) AS bridge_count
            WHERE bridge_count >= 2
            RETURN id, name, home_community, connected_communities, bridge_count
            ORDER BY bridge_count DESC
            LIMIT 20
            """,
            {},
        )

        bridges = [
            {
                "entity_id": r["id"],
                "entity_name": r["name"] or "",
                "home_community": r["home_community"],
                "connected_communities": r["connected_communities"],
                "bridge_count": r["bridge_count"],
            }
            for r in results
        ]

        logger.info("analytics.bridges_found", count=len(bridges))
        return bridges
