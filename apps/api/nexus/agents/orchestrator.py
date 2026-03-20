"""LangGraph orchestrator — builds and runs the NEXUS agent pipeline."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import structlog

from nexus.agents.state import NexusState

logger = structlog.get_logger()


def build_nexus_graph():
    """Build the LangGraph StateGraph for the NEXUS investigation pipeline.

    Pipeline: collector → extractor → analyst → verifier → END
    """
    from langgraph.graph import StateGraph, END

    from nexus.agents.collector_agent import collector_agent
    from nexus.agents.extractor_agent import extractor_agent
    from nexus.agents.analyst_agent import analyst_agent
    from nexus.agents.verifier_agent import verifier_agent

    graph = StateGraph(NexusState)

    # Add nodes
    graph.add_node("collector", collector_agent)
    graph.add_node("extractor", extractor_agent)
    graph.add_node("analyst", analyst_agent)
    graph.add_node("verifier", verifier_agent)

    # Add edges
    graph.set_entry_point("collector")
    graph.add_edge("collector", "extractor")
    graph.add_edge("extractor", "analyst")

    # Conditional: skip verifier if no entities found
    def should_verify(state: NexusState) -> str:
        resolved = state.get("resolved_entities", [])
        if not resolved:
            return "end"
        return "verifier"

    graph.add_conditional_edges("analyst", should_verify, {
        "verifier": "verifier",
        "end": END,
    })
    graph.add_edge("verifier", END)

    return graph.compile()


async def run_investigation(
    query: str,
    target_ints: list[str] | None = None,
    investigation_id: str | None = None,
    priority: str = "medium",
) -> NexusState:
    """Run a full NEXUS investigation pipeline.

    Args:
        query: The investigation query/target.
        target_ints: Which INT sources to use (default: all).
        investigation_id: Optional pre-assigned ID.
        priority: Investigation priority level.

    Returns:
        Final NexusState with all results.
    """
    if target_ints is None:
        target_ints = ["CYBINT", "SOCMINT", "SIGINT"]

    if investigation_id is None:
        investigation_id = f"inv-{uuid4().hex[:12]}"

    initial_state: NexusState = {
        "investigation_id": investigation_id,
        "query": query,
        "target_ints": target_ints,
        "priority": priority,
        "seed_entities": [],
        "collection_results": [],
        "extracted_entities": [],
        "extracted_relationships": [],
        "resolved_entities": [],
        "correlations": [],
        "communities": [],
        "centrality_scores": [],
        "patterns": [],
        "risk_assessments": [],
        "verified_entities": [],
        "verification_notes": [],
        "admiralty_grades": {},
        "combined_evidence": [],
        "report": "",
        "current_agent": "collector",
        "status": "collecting",
        "progress": 0,
        "errors": [],
        "messages": [],
    }

    logger.info(
        "orchestrator.starting",
        investigation_id=investigation_id,
        query=query,
        target_ints=target_ints,
    )

    try:
        app = build_nexus_graph()
        final_state = await app.ainvoke(initial_state)

        logger.info(
            "orchestrator.complete",
            investigation_id=investigation_id,
            status=final_state.get("status"),
            entity_count=len(final_state.get("verified_entities", [])),
        )
        return final_state

    except Exception as e:
        logger.error("orchestrator.failed", investigation_id=investigation_id, error=str(e))
        initial_state["status"] = "failed"
        initial_state["errors"] = [str(e)]
        return initial_state
