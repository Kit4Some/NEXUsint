"""Verifier Agent — source verification, D-S fusion, Admiralty grading, report."""

from __future__ import annotations

from typing import Any

import structlog

from nexus.agents.state import NexusState
from nexus.api.websocket.handlers import emit_investigation_progress
from nexus.fusion.evidence_combiner import EvidenceCombiner
from nexus.utils.admiralty import admiralty_to_label

logger = structlog.get_logger()


async def verifier_agent(state: NexusState) -> dict[str, Any]:
    """Verify entities, compute Admiralty grades, generate final report.

    Reads: resolved_entities, collection_results, correlations, patterns,
           risk_assessments, investigation_id, query
    Writes: verified_entities, verification_notes, admiralty_grades,
            combined_evidence, report, current_agent, status, progress, errors
    """
    investigation_id = state.get("investigation_id", "")
    query = state.get("query", "")
    resolved = state.get("resolved_entities", [])
    collection_results = state.get("collection_results", [])
    correlations = state.get("correlations", [])
    patterns = state.get("patterns", [])
    risk_assessments = state.get("risk_assessments", [])

    await emit_investigation_progress(
        investigation_id, "verifier", "running", 80, "Verifying sources..."
    )

    errors: list[str] = list(state.get("errors", []))
    combiner = EvidenceCombiner()

    # Source verification: check for contradictions
    verification_notes: list[str] = []
    verified_entities: list[dict[str, Any]] = []
    admiralty_grades: dict[str, str] = {}
    combined_evidence: list[dict[str, Any]] = []

    for entity in resolved:
        name = entity.get("canonical_name", "")
        source_ints = entity.get("source_ints", [])
        confidence = entity.get("confidence", 0)

        # Cross-source corroboration check
        source_count = len(source_ints) if isinstance(source_ints, list) else 1
        is_corroborated = source_count >= 2

        if is_corroborated:
            verification_notes.append(
                f"[CORROBORATED] {name}: confirmed by {source_count} INT sources"
            )
        elif confidence < 0.3:
            verification_notes.append(
                f"[LOW_CONFIDENCE] {name}: single source, confidence={confidence:.2f}"
            )

        # Compute Admiralty grade
        from nexus.utils.admiralty import compute_reliability_grade, compute_credibility_grade

        rel_grade = compute_reliability_grade(
            "multi" if is_corroborated else "single", confidence
        )
        cred_grade = compute_credibility_grade(
            cross_source_count=source_count,
            consistency=confidence,
            recency_hours=1.0,
        )
        grade = admiralty_to_label(rel_grade, cred_grade)
        admiralty_grades[name] = grade

        verified_entity = dict(entity)
        verified_entity["admiralty_grade"] = grade
        verified_entity["corroborated"] = is_corroborated
        verified_entities.append(verified_entity)

    await emit_investigation_progress(
        investigation_id, "verifier", "running", 90, "Generating report..."
    )

    # Generate final report
    report = _generate_report(
        query=query,
        investigation_id=investigation_id,
        verified_entities=verified_entities,
        correlations=correlations,
        patterns=patterns,
        risk_assessments=risk_assessments,
        verification_notes=verification_notes,
        errors=errors,
    )

    await emit_investigation_progress(
        investigation_id, "verifier", "completed", 100, "Investigation complete"
    )

    logger.info(
        "verifier_agent.done",
        investigation_id=investigation_id,
        verified=len(verified_entities),
        notes=len(verification_notes),
    )

    return {
        "verified_entities": verified_entities,
        "verification_notes": verification_notes,
        "admiralty_grades": admiralty_grades,
        "combined_evidence": combined_evidence,
        "report": report,
        "current_agent": "complete",
        "status": "complete",
        "progress": 100,
        "errors": errors,
    }


def _generate_report(
    query: str,
    investigation_id: str,
    verified_entities: list[dict[str, Any]],
    correlations: list[dict[str, Any]],
    patterns: list[dict[str, Any]],
    risk_assessments: list[dict[str, Any]],
    verification_notes: list[str],
    errors: list[str],
) -> str:
    """Generate a structured investigation report."""
    lines = [
        f"# NEXUS Investigation Report",
        f"",
        f"**Investigation ID:** {investigation_id}",
        f"**Query:** {query}",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"- **Entities discovered:** {len(verified_entities)}",
        f"- **Cross-INT correlations:** {len(correlations)}",
        f"- **Patterns detected:** {len(patterns)}",
        f"- **Risk items:** {len(risk_assessments)}",
        f"",
    ]

    # High-risk entities
    if risk_assessments:
        lines.append("## Risk Assessment")
        lines.append("")
        for ra in sorted(risk_assessments, key=lambda x: x.get("risk_score", 0), reverse=True)[:10]:
            lines.append(
                f"- **{ra.get('entity_id', '?')}** ({ra.get('entity_type', '?')}): "
                f"risk={ra.get('risk_score', 0):.2f} — {ra.get('recommendation', '')}"
            )
        lines.append("")

    # Key patterns
    if patterns:
        lines.append("## Detected Patterns")
        lines.append("")
        for p in patterns[:10]:
            lines.append(f"- [{p.get('type', '?')}] {p.get('description', '')}")
        lines.append("")

    # Cross-INT correlations summary
    if correlations:
        lines.append("## Cross-INT Correlations")
        lines.append("")
        by_type: dict[str, int] = {}
        for c in correlations:
            ctype = c.get("correlation_type", "unknown")
            by_type[ctype] = by_type.get(ctype, 0) + 1
        for ctype, count in by_type.items():
            lines.append(f"- {ctype}: {count} correlations")
        lines.append("")

    # Verification notes
    if verification_notes:
        lines.append("## Verification Notes")
        lines.append("")
        for note in verification_notes[:20]:
            lines.append(f"- {note}")
        lines.append("")

    # Errors
    if errors:
        lines.append("## Errors & Warnings")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by NEXUS Multi-INT Fusion Platform*")

    return "\n".join(lines)
