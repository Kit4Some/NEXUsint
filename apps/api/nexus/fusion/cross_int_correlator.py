"""Cross-INT correlation engine — temporal, spatial, graph-based."""

import math
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class CorrelationResult:
    """A correlation found between entities from different INT sources."""

    entity_a_id: str
    entity_b_id: str
    correlation_type: str  # "temporal", "spatial", "graph"
    score: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_a_id": self.entity_a_id,
            "entity_b_id": self.entity_b_id,
            "correlation_type": self.correlation_type,
            "score": self.score,
            "evidence": self.evidence,
        }


@dataclass
class Chain:
    """A cross-INT entity chain (e.g., IP → Location → Person)."""

    entity_ids: list[str]
    int_sequence: list[str]
    confidence: float


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute Haversine distance between two WGS84 points in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class CrossIntCorrelator:
    """Cross-INT correlation analysis engine."""

    def __init__(self, neo4j_client: Any = None, entity_repo: Any = None) -> None:
        self._neo4j = neo4j_client
        self._repo = entity_repo

    def correlate_temporal(
        self,
        entities: list[dict[str, Any]],
        window_hours: float = 24.0,
    ) -> list[CorrelationResult]:
        """Find entities from different INTs observed within a time window."""
        from datetime import datetime, timedelta

        results: list[CorrelationResult] = []
        window = timedelta(hours=window_hours)

        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1:]:
                # Must be from different INT sources
                if e1.get("source_int") == e2.get("source_int"):
                    continue

                t1 = e1.get("first_seen") or e1.get("created_at")
                t2 = e2.get("first_seen") or e2.get("created_at")

                if not t1 or not t2:
                    continue

                # Parse timestamps
                if isinstance(t1, str):
                    try:
                        t1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                if isinstance(t2, str):
                    try:
                        t2 = datetime.fromisoformat(t2.replace("Z", "+00:00"))
                    except ValueError:
                        continue

                diff = abs((t1 - t2).total_seconds())
                if diff <= window.total_seconds():
                    proximity = 1.0 - (diff / window.total_seconds())
                    results.append(CorrelationResult(
                        entity_a_id=e1.get("id", ""),
                        entity_b_id=e2.get("id", ""),
                        correlation_type="temporal",
                        score=proximity,
                        evidence={
                            "time_diff_seconds": diff,
                            "a_source": e1.get("source_int"),
                            "b_source": e2.get("source_int"),
                        },
                    ))

        logger.info("correlator.temporal", correlations=len(results))
        return results

    def correlate_spatial(
        self,
        entities: list[dict[str, Any]],
        max_distance_km: float = 50.0,
    ) -> list[CorrelationResult]:
        """Find entities from different INTs within spatial proximity."""
        results: list[CorrelationResult] = []

        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1:]:
                if e1.get("source_int") == e2.get("source_int"):
                    continue

                loc1 = e1.get("location") or {}
                loc2 = e2.get("location") or {}

                lat1 = loc1.get("latitude")
                lon1 = loc1.get("longitude")
                lat2 = loc2.get("latitude")
                lon2 = loc2.get("longitude")

                if None in (lat1, lon1, lat2, lon2):
                    continue

                distance = haversine_km(lat1, lon1, lat2, lon2)

                if distance <= max_distance_km:
                    proximity = 1.0 - (distance / max_distance_km)
                    results.append(CorrelationResult(
                        entity_a_id=e1.get("id", ""),
                        entity_b_id=e2.get("id", ""),
                        correlation_type="spatial",
                        score=proximity,
                        evidence={
                            "distance_km": round(distance, 2),
                            "a_source": e1.get("source_int"),
                            "b_source": e2.get("source_int"),
                        },
                    ))

        logger.info("correlator.spatial", correlations=len(results))
        return results

    async def correlate_graph(
        self,
        entity_id: str,
        max_hops: int = 3,
    ) -> list[CorrelationResult]:
        """Find cross-INT connected entities via graph traversal."""
        if not self._neo4j:
            return []

        query = """
        MATCH path = (start)-[*1..{max_hops}]-(end)
        WHERE start.id = $entity_id
          AND start.source_int <> end.source_int
        RETURN end.id AS end_id,
               end.source_int AS end_source,
               length(path) AS hops,
               [r IN relationships(path) | type(r)] AS rel_types
        LIMIT 100
        """.replace("{max_hops}", str(max_hops))

        try:
            records = await self._neo4j.execute_read(query, {"entity_id": entity_id})
        except Exception as e:
            logger.warning("correlator.graph_failed", error=str(e))
            return []

        results: list[CorrelationResult] = []
        for record in records:
            hops = record.get("hops", max_hops)
            score = 1.0 - ((hops - 1) / max_hops)
            results.append(CorrelationResult(
                entity_a_id=entity_id,
                entity_b_id=record.get("end_id", ""),
                correlation_type="graph",
                score=max(score, 0.1),
                evidence={
                    "hops": hops,
                    "relationship_types": record.get("rel_types", []),
                    "end_source": record.get("end_source"),
                },
            ))

        logger.info("correlator.graph", entity_id=entity_id, correlations=len(results))
        return results

    def compute_correlation_matrix(
        self, entities: list[dict[str, Any]]
    ) -> dict[str, dict[str, int]]:
        """Compute a 4x4 cross-INT correlation count matrix."""
        int_types = ["CYBINT", "SOCMINT", "SIGINT", "GEOINT"]
        matrix: dict[str, dict[str, int]] = {
            a: {b: 0 for b in int_types} for a in int_types
        }

        # Count temporal + spatial correlations
        temporal = self.correlate_temporal(entities)
        spatial = self.correlate_spatial(entities)

        entity_map = {e.get("id", ""): e for e in entities}

        for corr in temporal + spatial:
            a = entity_map.get(corr.entity_a_id, {})
            b = entity_map.get(corr.entity_b_id, {})
            src_a = a.get("source_int", "")
            src_b = b.get("source_int", "")

            if src_a in int_types and src_b in int_types:
                matrix[src_a][src_b] += 1
                matrix[src_b][src_a] += 1

        return matrix
