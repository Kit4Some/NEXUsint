"""LangGraph agent state definition for NEXUS investigation pipeline."""

from __future__ import annotations

from typing import Any, TypedDict


class NexusState(TypedDict, total=False):
    """Shared state flowing through the NEXUS multi-agent pipeline.

    Each agent reads from and writes to this state. LangGraph manages
    the transitions between agents based on the graph definition.
    """

    # --- Investigation metadata ---
    investigation_id: str
    query: str
    target_ints: list[str]  # e.g. ["CYBINT", "SOCMINT", "SIGINT", "GEOINT"]
    priority: str  # "low", "medium", "high", "critical"

    # --- Collection phase ---
    seed_entities: list[dict[str, Any]]
    collection_results: list[dict[str, Any]]

    # --- Extraction phase ---
    extracted_entities: list[dict[str, Any]]
    extracted_relationships: list[dict[str, Any]]
    resolved_entities: list[dict[str, Any]]

    # --- Analysis phase ---
    correlations: list[dict[str, Any]]
    communities: list[dict[str, Any]]
    centrality_scores: list[dict[str, Any]]
    patterns: list[dict[str, Any]]
    risk_assessments: list[dict[str, Any]]

    # --- Verification phase ---
    verified_entities: list[dict[str, Any]]
    verification_notes: list[str]
    admiralty_grades: dict[str, str]
    combined_evidence: list[dict[str, Any]]

    # --- Output ---
    report: str

    # --- Pipeline control ---
    current_agent: str
    status: str  # "pending", "collecting", "extracting", "analyzing", "verifying", "complete", "failed"
    progress: int  # 0-100
    errors: list[str]
    messages: list[dict[str, str]]
