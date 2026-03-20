"""Advanced anomaly detection — statistical, graph, and temporal methods."""

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog

from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.analytics.feature_extractor import FeatureExtractor

logger = structlog.get_logger()


@dataclass
class Anomaly:
    entity_id: str
    entity_name: str
    anomaly_type: str
    score: float
    evidence: dict[str, Any] = field(default_factory=dict)


class AnomalyDetector:
    """Multi-method anomaly detection for intelligence entities."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client
        self._extractor = FeatureExtractor(client)

    async def detect_all(
        self,
        methods: list[str] | None = None,
        limit: int = 500,
    ) -> list[Anomaly]:
        """Run all requested anomaly detection methods and merge results."""
        methods = methods or ["statistical", "graph", "temporal"]
        anomalies: list[Anomaly] = []

        if "statistical" in methods:
            anomalies.extend(await self.detect_statistical_outliers(limit=limit))

        if "graph" in methods:
            anomalies.extend(await self.detect_graph_anomalies())
            anomalies.extend(await self.detect_bridge_entities())

        if "temporal" in methods:
            anomalies.extend(await self.detect_temporal_spikes())

        # Deduplicate by (entity_id, anomaly_type)
        seen: set[tuple[str, str]] = set()
        unique: list[Anomaly] = []
        for a in anomalies:
            key = (a.entity_id, a.anomaly_type)
            if key not in seen:
                seen.add(key)
                unique.append(a)

        unique.sort(key=lambda a: a.score, reverse=True)
        logger.info("analytics.anomalies_detected", count=len(unique))
        return unique

    async def detect_statistical_outliers(
        self,
        contamination: float = 0.1,
        limit: int = 500,
    ) -> list[Anomaly]:
        """Detect outliers using z-score on entity feature vectors."""
        features, ids, names = await self._extractor.extract_entity_features(limit=limit)
        if features.shape[0] < 5:
            return []

        anomalies: list[Anomaly] = []

        # Z-score method
        mean = np.mean(features, axis=0)
        std = np.std(features, axis=0)
        std[std == 0] = 1.0  # avoid division by zero

        z_scores = np.abs((features - mean) / std)
        max_z = np.max(z_scores, axis=1)

        threshold = 2.5
        for i in range(len(ids)):
            if max_z[i] > threshold:
                feature_names = ["confidence", "risk_score", "degree", "in_degree", "out_degree", "rel_type_count", "source_count"]
                outlier_features = {
                    feature_names[j]: round(float(z_scores[i][j]), 2)
                    for j in range(len(feature_names))
                    if z_scores[i][j] > threshold
                }
                anomalies.append(Anomaly(
                    entity_id=ids[i],
                    entity_name=names[i],
                    anomaly_type="statistical_outlier",
                    score=round(float(max_z[i]), 3),
                    evidence={"z_scores": outlier_features, "threshold": threshold},
                ))

        # Isolation Forest (if sklearn available)
        try:
            from sklearn.ensemble import IsolationForest
            iso = IsolationForest(contamination=contamination, random_state=42)
            predictions = iso.fit_predict(features)
            iso_scores = -iso.score_samples(features)

            for i in range(len(ids)):
                if predictions[i] == -1:
                    # Check if already flagged by z-score
                    if not any(a.entity_id == ids[i] and a.anomaly_type == "statistical_outlier" for a in anomalies):
                        anomalies.append(Anomaly(
                            entity_id=ids[i],
                            entity_name=names[i],
                            anomaly_type="isolation_forest",
                            score=round(float(iso_scores[i]), 3),
                            evidence={"method": "isolation_forest", "contamination": contamination},
                        ))
        except ImportError:
            logger.debug("analytics.sklearn_not_available")

        return anomalies

    async def detect_graph_anomalies(self) -> list[Anomaly]:
        """Detect entities with unexpected connection patterns."""
        results = await self._client.execute_read(
            """
            MATCH (e)
            WHERE e.id IS NOT NULL
            OPTIONAL MATCH (e)-[r]-()
            WITH e, count(r) AS degree,
                 count(DISTINCT type(r)) AS rel_types
            WHERE degree > 0
            WITH avg(degree) AS mean_deg, stDev(degree) AS std_deg,
                 collect({id: e.id, name: e.name, degree: degree, rel_types: rel_types}) AS entities
            UNWIND entities AS ent
            WITH ent, mean_deg, std_deg
            WHERE ent.degree > mean_deg + 2 * std_deg OR ent.rel_types >= 5
            RETURN ent.id AS id, ent.name AS name,
                   ent.degree AS degree, ent.rel_types AS rel_types,
                   mean_deg, std_deg
            ORDER BY ent.degree DESC
            LIMIT 20
            """,
            {},
        )

        anomalies: list[Anomaly] = []
        for r in results:
            z = (r["degree"] - r["mean_deg"]) / max(r["std_deg"], 1)
            anomalies.append(Anomaly(
                entity_id=r["id"],
                entity_name=r["name"] or "",
                anomaly_type="graph_structural",
                score=round(float(z), 3),
                evidence={
                    "degree": r["degree"],
                    "rel_types": r["rel_types"],
                    "mean_degree": round(float(r["mean_deg"]), 2),
                },
            ))

        return anomalies

    async def detect_bridge_entities(self) -> list[Anomaly]:
        """Detect entities bridging otherwise disconnected communities."""
        results = await self._client.execute_read(
            """
            CALL gds.betweennessCentrality.stream('entity-graph')
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            WHERE score > 0
            WITH avg(score) AS mean_bc, stDev(score) AS std_bc,
                 collect({id: node.id, name: node.name, bc: score}) AS nodes
            UNWIND nodes AS n
            WITH n, mean_bc, std_bc
            WHERE n.bc > mean_bc + 2 * std_bc
            RETURN n.id AS id, n.name AS name, n.bc AS betweenness,
                   mean_bc, std_bc
            ORDER BY n.bc DESC
            LIMIT 10
            """,
            {},
        )

        anomalies: list[Anomaly] = []
        for r in results:
            anomalies.append(Anomaly(
                entity_id=r["id"],
                entity_name=r["name"] or "",
                anomaly_type="bridge_entity",
                score=round(float(r["betweenness"]), 3),
                evidence={
                    "betweenness_centrality": round(float(r["betweenness"]), 4),
                    "mean_bc": round(float(r["mean_bc"]), 4),
                },
            ))

        return anomalies

    async def detect_temporal_spikes(
        self,
        window_hours: int = 24,
        threshold_sigma: float = 3.0,
    ) -> list[Anomaly]:
        """Detect entities with abnormal temporal activity spikes."""
        results = await self._client.execute_read(
            """
            MATCH (e)-[r]-()
            WHERE r.created_at IS NOT NULL AND e.id IS NOT NULL
            WITH e, r.created_at AS ts
            ORDER BY ts
            WITH e, collect(ts) AS timestamps
            WHERE size(timestamps) >= 5
            RETURN e.id AS id, e.name AS name, timestamps
            LIMIT 100
            """,
            {},
        )

        anomalies: list[Anomaly] = []
        for r in results:
            timestamps = r["timestamps"]
            if len(timestamps) < 5:
                continue

            # Calculate inter-event intervals
            try:
                intervals = []
                for i in range(1, len(timestamps)):
                    t1, t2 = str(timestamps[i - 1]), str(timestamps[i])
                    if t1 and t2:
                        intervals.append(1.0)  # simplified: count as 1 unit per event

                if len(intervals) < 3:
                    continue

                arr = np.array(intervals)
                mean_interval = float(np.mean(arr))
                std_interval = float(np.std(arr))

                if std_interval > 0 and mean_interval > 0:
                    burstiness = (std_interval - mean_interval) / (std_interval + mean_interval)
                    if burstiness > 0.5:
                        anomalies.append(Anomaly(
                            entity_id=r["id"],
                            entity_name=r["name"] or "",
                            anomaly_type="temporal_spike",
                            score=round(burstiness, 3),
                            evidence={
                                "event_count": len(timestamps),
                                "burstiness": round(burstiness, 3),
                            },
                        ))
            except Exception:
                continue

        return anomalies
