"""Evidence combiner — orchestrates D-S fusion + Admiralty grading."""

from dataclasses import dataclass, field
from typing import Any

import structlog

from nexus.collectors.base import CollectionResult
from nexus.fusion.dempster_shafer import DempsterShaferEngine, MassFunction
from nexus.utils.admiralty import (
    compute_confidence_score,
    compute_credibility_grade,
    compute_reliability_grade,
    admiralty_to_label,
)

logger = structlog.get_logger()

# Source type → base reliability mapping
SOURCE_RELIABILITY: dict[str, float] = {
    "shodan": 0.85,
    "virustotal": 0.90,
    "abuseipdb": 0.80,
    "alienvault_otx": 0.75,
    "dns": 0.90,
    "certificate": 0.95,
    "twitter": 0.50,
    "telegram": 0.45,
    "reddit": 0.40,
    "cross_platform_resolver": 0.35,
    "adsb": 0.85,
    "ais": 0.80,
    "sentinel": 0.90,
    "overpass": 0.85,
    "nominatim": 0.80,
    "geoip": 0.70,
    "exif": 0.95,
}


@dataclass
class CombinedEvidence:
    """Result of combining evidence from multiple sources for an entity."""

    entity_id: str
    combined_confidence: float
    belief: float
    plausibility: float
    uncertainty: float
    admiralty_grade: str
    source_count: int
    conflict_level: float
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "combined_confidence": round(self.combined_confidence, 4),
            "belief": round(self.belief, 4),
            "plausibility": round(self.plausibility, 4),
            "uncertainty": round(self.uncertainty, 4),
            "admiralty_grade": self.admiralty_grade,
            "source_count": self.source_count,
            "conflict_level": round(self.conflict_level, 4),
            "sources": self.sources,
        }


@dataclass
class ConflictReport:
    """Report of conflicting evidence between sources."""

    entity_id: str
    nature: str
    severity: float
    sources: list[str] = field(default_factory=list)
    recommendation: str = ""


class EvidenceCombiner:
    """Combines multi-source evidence using Dempster-Shafer + Admiralty grading."""

    def __init__(self) -> None:
        self._ds = DempsterShaferEngine()

    def combine_entity_evidence(
        self,
        entity_id: str,
        sources: list[CollectionResult],
    ) -> CombinedEvidence:
        """Combine all evidence for a single entity from multiple sources."""
        if not sources:
            return CombinedEvidence(
                entity_id=entity_id,
                combined_confidence=0.0,
                belief=0.0,
                plausibility=1.0,
                uncertainty=1.0,
                admiralty_grade="F6",
                source_count=0,
                conflict_level=0.0,
            )

        # Convert each source into a mass function
        mass_functions: list[MassFunction] = []
        source_names: list[str] = []
        max_conflict = 0.0

        for source in sources:
            collector = source.metadata.get("collector", "unknown")
            reliability = SOURCE_RELIABILITY.get(collector, 0.5)
            source_names.append(f"{source.source_int}:{collector}")

            mf = self._ds.evidence_to_mass(
                source_reliability=reliability,
                supports_hypothesis=True,
            )
            mass_functions.append(mf)

        # Check pairwise conflict
        for i, mf1 in enumerate(mass_functions):
            for mf2 in mass_functions[i + 1:]:
                conflict = self._ds.conflict_level(mf1, mf2)
                max_conflict = max(max_conflict, conflict)

        # Combine all evidence
        combined = self._ds.combine_multiple(mass_functions)

        hypothesis = frozenset(["TRUE"])
        belief = self._ds.belief(combined, hypothesis)
        plausibility = self._ds.plausibility(combined, hypothesis)
        uncertainty = plausibility - belief

        # Compute practical confidence score
        source_ints = set(s.source_int for s in sources)
        cross_corroboration = min(len(source_ints) / 4.0, 1.0)

        # Recency: average freshness (simplified)
        recency = 0.8  # Default; could compute from timestamps

        confidence = compute_confidence_score(
            source_reliability=belief,
            cross_corroboration=cross_corroboration,
            recency_factor=recency,
            consistency=1.0 - max_conflict,
        )

        # Admiralty grading
        rel_grade = compute_reliability_grade("multi", belief)
        cred_grade = compute_credibility_grade(
            cross_source_count=len(set(source_names)),
            consistency=1.0 - max_conflict,
            recency_hours=1.0,
        )
        admiralty = admiralty_to_label(rel_grade, cred_grade)

        return CombinedEvidence(
            entity_id=entity_id,
            combined_confidence=confidence,
            belief=belief,
            plausibility=plausibility,
            uncertainty=uncertainty,
            admiralty_grade=admiralty,
            source_count=len(sources),
            conflict_level=max_conflict,
            sources=source_names,
        )

    def resolve_conflicts(
        self,
        evidences: list[CombinedEvidence],
        conflict_threshold: float = 0.3,
    ) -> list[ConflictReport]:
        """Identify entities with significant evidence conflicts."""
        reports: list[ConflictReport] = []

        for evidence in evidences:
            if evidence.conflict_level >= conflict_threshold:
                severity = evidence.conflict_level

                if severity > 0.7:
                    recommendation = "Manual review required — high conflict between sources"
                elif severity > 0.5:
                    recommendation = "Investigate source disagreement — moderate conflict"
                else:
                    recommendation = "Minor conflict — consider source reliability differences"

                reports.append(ConflictReport(
                    entity_id=evidence.entity_id,
                    nature=f"Source conflict (K={evidence.conflict_level:.2f})",
                    severity=severity,
                    sources=evidence.sources,
                    recommendation=recommendation,
                ))

        logger.info("evidence_combiner.conflicts", count=len(reports))
        return reports
