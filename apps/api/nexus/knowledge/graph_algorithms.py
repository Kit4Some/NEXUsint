"""Neo4j Graph Data Science (GDS) algorithm wrappers."""

from typing import Any

import structlog

from nexus.knowledge.neo4j_client import Neo4jClient

logger = structlog.get_logger()

GRAPH_PROJECTION = "nexus-entities"


class GraphAlgorithms:
    """Wrapper for Neo4j GDS graph algorithms."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    async def _ensure_projection(self) -> None:
        """Create the GDS graph projection if it doesn't exist."""
        check = await self._client.execute_read(
            "CALL gds.graph.exists($name) YIELD exists",
            {"name": GRAPH_PROJECTION},
        )
        if check and not check[0].get("exists"):
            await self._client.execute_write(
                """
                CALL gds.graph.project(
                    $name,
                    'Entity',
                    {
                        RESOLVES_TO: {orientation: 'NATURAL'},
                        HOSTS: {orientation: 'NATURAL'},
                        COMMUNICATES_WITH: {orientation: 'NATURAL'},
                        ATTRIBUTED_TO: {orientation: 'NATURAL'},
                        TARGETS: {orientation: 'NATURAL'},
                        USES: {orientation: 'NATURAL'},
                        PART_OF: {orientation: 'NATURAL'},
                        LOCATED_AT: {orientation: 'NATURAL'},
                        REGISTERED_BY: {orientation: 'NATURAL'},
                        CORROBORATED_BY: {orientation: 'NATURAL'}
                    }
                )
                """,
                {"name": GRAPH_PROJECTION},
            )

    async def run_pagerank(self, max_iterations: int = 20) -> list[dict[str, Any]]:
        """Run PageRank and return top entities by centrality."""
        await self._ensure_projection()

        results = await self._client.execute_read(
            """
            CALL gds.pageRank.stream($name, {maxIterations: $max_iter})
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            RETURN node.id AS id, node.name AS name, node.type AS type, score
            ORDER BY score DESC
            LIMIT 50
            """,
            {"name": GRAPH_PROJECTION, "max_iter": max_iterations},
        )
        return results

    async def run_louvain(self) -> list[dict[str, Any]]:
        """Run Louvain community detection."""
        await self._ensure_projection()

        results = await self._client.execute_read(
            """
            CALL gds.louvain.stream($name)
            YIELD nodeId, communityId
            WITH gds.util.asNode(nodeId) AS node, communityId
            RETURN node.id AS id, node.name AS name, node.type AS type, communityId
            ORDER BY communityId, node.name
            """,
            {"name": GRAPH_PROJECTION},
        )
        return results

    async def run_betweenness_centrality(self) -> list[dict[str, Any]]:
        """Run Betweenness Centrality."""
        await self._ensure_projection()

        results = await self._client.execute_read(
            """
            CALL gds.betweenness.stream($name)
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            RETURN node.id AS id, node.name AS name, node.type AS type, score
            ORDER BY score DESC
            LIMIT 50
            """,
            {"name": GRAPH_PROJECTION},
        )
        return results

    async def find_shortest_path(
        self, source_id: str, target_id: str
    ) -> list[dict[str, Any]]:
        """Find shortest path between two entities."""
        results = await self._client.execute_read(
            """
            MATCH (source:Entity {id: $source_id}), (target:Entity {id: $target_id})
            MATCH path = shortestPath((source)-[*..10]-(target))
            UNWIND nodes(path) AS node
            RETURN node.id AS id, node.name AS name, node.type AS type
            """,
            {"source_id": source_id, "target_id": target_id},
        )
        return results
