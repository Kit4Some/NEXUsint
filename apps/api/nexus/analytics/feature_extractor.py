"""Feature extraction for entity-level anomaly detection."""

from typing import Any

import numpy as np
import structlog

from nexus.knowledge.neo4j_client import Neo4jClient

logger = structlog.get_logger()


class FeatureExtractor:
    """Extracts numerical feature vectors from entities for ML-based analysis."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    async def extract_entity_features(
        self,
        entity_ids: list[str] | None = None,
        limit: int = 1000,
    ) -> tuple[np.ndarray, list[str], list[str]]:
        """Extract feature matrix for entities.

        Returns:
            (feature_matrix, entity_ids, entity_names)
            Feature columns: confidence, risk_score, degree, in_degree, out_degree,
                             relationship_type_count, source_count
        """
        id_filter = "WHERE e.id IN $ids" if entity_ids else ""
        params: dict[str, Any] = {"limit": limit}
        if entity_ids:
            params["ids"] = entity_ids

        results = await self._client.execute_read(
            f"""
            MATCH (e)
            {id_filter}
            WITH e LIMIT $limit
            OPTIONAL MATCH (e)-[r_out]->()
            OPTIONAL MATCH ()-[r_in]->(e)
            WITH e,
                 count(DISTINCT r_out) AS out_degree,
                 count(DISTINCT r_in) AS in_degree,
                 count(DISTINCT type(r_out)) + count(DISTINCT type(r_in)) AS rel_type_count
            RETURN e.id AS id,
                   e.name AS name,
                   coalesce(e.confidence, 0.5) AS confidence,
                   coalesce(e.riskScore, 0.0) AS risk_score,
                   out_degree + in_degree AS degree,
                   in_degree,
                   out_degree,
                   rel_type_count
            """,
            params,
        )

        if not results:
            return np.empty((0, 7)), [], []

        ids = [r["id"] for r in results]
        names = [r["name"] or "" for r in results]

        features = np.array([
            [
                r["confidence"],
                r["risk_score"],
                r["degree"],
                r["in_degree"],
                r["out_degree"],
                r["rel_type_count"],
                1.0,  # placeholder for source_count
            ]
            for r in results
        ], dtype=np.float64)

        logger.info("analytics.features_extracted", entity_count=len(ids), feature_dim=features.shape[1])
        return features, ids, names

    async def extract_temporal_features(self, entity_id: str) -> dict[str, Any]:
        """Extract temporal activity pattern for a single entity."""
        results = await self._client.execute_read(
            """
            MATCH (e {id: $entityId})-[r]-()
            WHERE r.created_at IS NOT NULL
            RETURN r.created_at AS timestamp, type(r) AS rel_type
            ORDER BY r.created_at
            """,
            {"entityId": entity_id},
        )

        timestamps = [r["timestamp"] for r in results if r["timestamp"]]
        rel_types = [r["rel_type"] for r in results]

        return {
            "entity_id": entity_id,
            "event_count": len(timestamps),
            "timestamps": timestamps,
            "relationship_types": list(set(rel_types)),
            "unique_rel_types": len(set(rel_types)),
        }
