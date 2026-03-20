"""Report section builders for intelligence reports."""

from collections import Counter, defaultdict
from typing import Any

from nexus.utils.admiralty import compute_reliability_grade


class ReportSections:
    """Builds individual sections for intelligence reports."""

    def executive_summary(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        investigation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """High-level investigation summary."""
        type_counts = Counter(e.get("type", "Unknown") for e in entities)
        avg_confidence = (
            sum(e.get("confidence", 0.0) for e in entities) / len(entities)
            if entities else 0.0
        )
        high_risk = [e for e in entities if e.get("riskScore", e.get("risk_score", 0)) >= 7.0]

        summary = {
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "entity_type_breakdown": dict(type_counts),
            "average_confidence": round(avg_confidence, 3),
            "high_risk_entity_count": len(high_risk),
            "summary": (
                f"Investigation identified {len(entities)} entities across "
                f"{len(type_counts)} types with {len(relationships)} relationships. "
                f"Average confidence: {avg_confidence:.1%}. "
                f"{len(high_risk)} high-risk entities flagged."
            ),
        }

        if investigation:
            summary["query"] = investigation.get("query", "")
            summary["status"] = investigation.get("status", "")
            summary["target_ints"] = investigation.get("target_ints", [])

        return summary

    def entity_analysis(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        """Entities grouped by type with confidence and risk details."""
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for entity in entities:
            entity_type = entity.get("type", "Unknown")
            confidence = entity.get("confidence", 0.0)
            risk = entity.get("riskScore", entity.get("risk_score", 0.0))
            source_int = entity.get("sourceInt", entity.get("source_int", "UNKNOWN"))

            grouped[entity_type].append({
                "id": entity.get("id", ""),
                "name": entity.get("name", ""),
                "confidence": round(confidence, 3),
                "risk_score": round(risk, 2),
                "source_int": source_int,
                "reliability_grade": compute_reliability_grade(source_int, confidence),
            })

        # Sort each group by risk descending
        for entities_list in grouped.values():
            entities_list.sort(key=lambda e: e["risk_score"], reverse=True)

        return {
            "groups": {k: v for k, v in sorted(grouped.items())},
            "total_types": len(grouped),
        }

    def relationship_graph_summary(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Graph topology summary: centrality, key connections."""
        # Compute degree centrality
        degree: Counter[str] = Counter()
        rel_type_counts: Counter[str] = Counter()

        for rel in relationships:
            source = rel.get("source_id", rel.get("source", ""))
            target = rel.get("target_id", rel.get("target", ""))
            degree[source] += 1
            degree[target] += 1
            rel_type_counts[rel.get("type", "UNKNOWN")] += 1

        entity_names = {e.get("id", ""): e.get("name", "") for e in entities}
        top_nodes = [
            {"id": node_id, "name": entity_names.get(node_id, node_id), "degree": deg}
            for node_id, deg in degree.most_common(10)
        ]

        return {
            "node_count": len(entities),
            "edge_count": len(relationships),
            "relationship_type_breakdown": dict(rel_type_counts),
            "top_connected_nodes": top_nodes,
            "density": (
                (2 * len(relationships)) / (len(entities) * (len(entities) - 1))
                if len(entities) > 1 else 0.0
            ),
        }

    def timeline_section(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        """Temporal distribution of entities."""
        events: list[dict[str, Any]] = []
        for entity in entities:
            created = entity.get("created_at", entity.get("created", ""))
            if created:
                events.append({
                    "id": entity.get("id", ""),
                    "name": entity.get("name", ""),
                    "type": entity.get("type", ""),
                    "timestamp": created,
                })

        events.sort(key=lambda e: e["timestamp"])

        return {
            "event_count": len(events),
            "events": events[:100],  # Cap at 100 for readability
            "earliest": events[0]["timestamp"] if events else None,
            "latest": events[-1]["timestamp"] if events else None,
        }

    def risk_assessment(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        """Risk matrix and high-risk entity listing."""
        risk_buckets: dict[str, list[dict[str, Any]]] = {
            "critical": [],  # >= 9.0
            "high": [],      # >= 7.0
            "medium": [],    # >= 4.0
            "low": [],       # >= 0.0
        }

        for entity in entities:
            risk = entity.get("riskScore", entity.get("risk_score", 0.0))
            entry = {
                "id": entity.get("id", ""),
                "name": entity.get("name", ""),
                "type": entity.get("type", ""),
                "risk_score": round(risk, 2),
                "confidence": round(entity.get("confidence", 0.0), 3),
            }
            if risk >= 9.0:
                risk_buckets["critical"].append(entry)
            elif risk >= 7.0:
                risk_buckets["high"].append(entry)
            elif risk >= 4.0:
                risk_buckets["medium"].append(entry)
            else:
                risk_buckets["low"].append(entry)

        # Sort each bucket by risk descending
        for bucket in risk_buckets.values():
            bucket.sort(key=lambda e: e["risk_score"], reverse=True)

        total = len(entities) or 1
        return {
            "risk_distribution": {k: len(v) for k, v in risk_buckets.items()},
            "risk_percentages": {
                k: round(len(v) / total * 100, 1)
                for k, v in risk_buckets.items()
            },
            "critical_entities": risk_buckets["critical"],
            "high_risk_entities": risk_buckets["high"],
        }

    def confidence_metrics(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        """Admiralty grade breakdown and confidence distribution."""
        grade_counts: Counter[str] = Counter()
        int_confidence: dict[str, list[float]] = defaultdict(list)

        for entity in entities:
            confidence = entity.get("confidence", 0.0)
            source_int = entity.get("sourceInt", entity.get("source_int", "UNKNOWN"))
            grade = compute_reliability_grade(source_int, confidence)
            grade_counts[grade] += 1
            int_confidence[source_int].append(confidence)

        int_averages = {
            source: round(sum(vals) / len(vals), 3)
            for source, vals in int_confidence.items()
        }

        return {
            "admiralty_grade_distribution": dict(grade_counts),
            "confidence_by_int": int_averages,
            "overall_average": round(
                sum(e.get("confidence", 0.0) for e in entities) / max(len(entities), 1), 3
            ),
            "entity_count_by_int": {k: len(v) for k, v in int_confidence.items()},
        }

    def conflict_notes(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        """Identify entities with conflicting evidence or low agreement."""
        conflicts: list[dict[str, Any]] = []

        # Group entities by name to find duplicates with different sources
        name_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entity in entities:
            name = entity.get("name", "").lower().strip()
            if name:
                name_groups[name].append(entity)

        for name, group in name_groups.items():
            if len(group) < 2:
                continue
            confidences = [e.get("confidence", 0.0) for e in group]
            spread = max(confidences) - min(confidences)
            if spread > 0.3:
                conflicts.append({
                    "name": group[0].get("name", ""),
                    "entity_count": len(group),
                    "confidence_spread": round(spread, 3),
                    "sources": list({
                        e.get("sourceInt", e.get("source_int", ""))
                        for e in group
                    }),
                    "note": f"Confidence spread of {spread:.1%} across {len(group)} sources",
                })

        # Flag low-confidence entities
        low_conf = [
            {
                "id": e.get("id", ""),
                "name": e.get("name", ""),
                "confidence": round(e.get("confidence", 0.0), 3),
                "source_int": e.get("sourceInt", e.get("source_int", "")),
            }
            for e in entities
            if e.get("confidence", 0.0) < 0.3
        ]

        return {
            "conflicting_entities": conflicts,
            "low_confidence_entities": low_conf[:20],
            "conflict_count": len(conflicts),
            "low_confidence_count": len(low_conf),
        }

    def recommendations(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate actionable intelligence recommendations."""
        recs: list[dict[str, str]] = []

        # Check for high-risk, low-confidence entities
        uncertain_risks = [
            e for e in entities
            if e.get("riskScore", e.get("risk_score", 0)) >= 7.0
            and e.get("confidence", 0.0) < 0.5
        ]
        if uncertain_risks:
            names = ", ".join(e.get("name", "") for e in uncertain_risks[:5])
            recs.append({
                "priority": "high",
                "category": "verification",
                "recommendation": (
                    f"Prioritize verification of {len(uncertain_risks)} high-risk entities "
                    f"with low confidence: {names}"
                ),
            })

        # Check for isolated entities (no relationships)
        connected_ids = set()
        for rel in relationships:
            connected_ids.add(rel.get("source_id", rel.get("source", "")))
            connected_ids.add(rel.get("target_id", rel.get("target", "")))

        isolated = [e for e in entities if e.get("id", "") not in connected_ids]
        if isolated:
            recs.append({
                "priority": "medium",
                "category": "collection",
                "recommendation": (
                    f"{len(isolated)} entities have no relationships. "
                    "Consider additional collection to establish connections."
                ),
            })

        # Check INT coverage
        ints = {e.get("sourceInt", e.get("source_int", "")) for e in entities}
        missing = {"CYBINT", "SOCMINT", "SIGINT", "GEOINT"} - ints
        if missing:
            recs.append({
                "priority": "low",
                "category": "coverage",
                "recommendation": (
                    f"No data from {', '.join(sorted(missing))}. "
                    "Consider broadening collection sources."
                ),
            })

        # Overall confidence recommendation
        avg_conf = (
            sum(e.get("confidence", 0.0) for e in entities) / len(entities)
            if entities else 0.0
        )
        if avg_conf < 0.5:
            recs.append({
                "priority": "high",
                "category": "confidence",
                "recommendation": (
                    f"Overall average confidence is low ({avg_conf:.1%}). "
                    "Additional corroboration recommended before dissemination."
                ),
            })

        return {
            "recommendations": recs,
            "total_count": len(recs),
        }
