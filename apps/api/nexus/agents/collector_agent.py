"""Collector Agent — dispatches queries to INT-specific collectors."""

from __future__ import annotations

from typing import Any

import structlog

from nexus.agents.state import NexusState
from nexus.api.websocket.handlers import emit_investigation_progress
from nexus.collectors.base import CollectionQuery

logger = structlog.get_logger()


async def collector_agent(state: NexusState) -> dict[str, Any]:
    """Dispatch collection to appropriate INT managers based on target_ints.

    Reads: query, target_ints, seed_entities
    Writes: collection_results, current_agent, status, progress, errors
    """
    investigation_id = state.get("investigation_id", "")
    query = state.get("query", "")
    target_ints = state.get("target_ints", [])

    await emit_investigation_progress(
        investigation_id, "collector", "running", 5, "Starting collection..."
    )

    all_results: list[dict[str, Any]] = []
    errors: list[str] = list(state.get("errors", []))

    # Collect from each requested INT
    for int_type in target_ints:
        try:
            results = await _collect_for_int(int_type, query)
            all_results.extend(results)
            await emit_investigation_progress(
                investigation_id,
                "collector",
                "running",
                10 + len(all_results) % 15,
                f"Collected {len(results)} results from {int_type}",
            )
        except Exception as e:
            msg = f"{int_type} collection failed: {e}"
            logger.warning("collector_agent.int_failed", int_type=int_type, error=str(e))
            errors.append(msg)

    await emit_investigation_progress(
        investigation_id,
        "collector",
        "completed",
        25,
        f"Collection complete — {len(all_results)} results from {len(target_ints)} INT sources",
    )

    logger.info(
        "collector_agent.done",
        investigation_id=investigation_id,
        result_count=len(all_results),
    )

    return {
        "collection_results": all_results,
        "current_agent": "extractor",
        "status": "extracting",
        "progress": 25,
        "errors": errors,
    }


async def _collect_for_int(int_type: str, query: str) -> list[dict[str, Any]]:
    """Run collection for a specific INT type."""
    results: list[dict[str, Any]] = []

    if int_type == "CYBINT":
        from nexus.collectors.cybint.manager import CybintManager

        mgr = CybintManager()
        try:
            collected = await mgr.collect(query, scan_type="full")
            results.extend(r.model_dump() for r in collected)
        finally:
            await mgr.close()

    elif int_type == "SOCMINT":
        from nexus.collectors.socmint.manager import SocmintManager

        mgr = SocmintManager()
        try:
            collected = await mgr.collect(query, scan_type="full")
            results.extend(r.model_dump() for r in collected)
        finally:
            await mgr.close()

    elif int_type == "SIGINT":
        from nexus.collectors.sigint.manager import SigntManager

        mgr = SigntManager()
        try:
            collected = await mgr.collect(query, scan_type="full")
            results.extend(r.model_dump() for r in collected)
        finally:
            await mgr.close()

    elif int_type == "GEOINT":
        # GEOINT uses SIGINT spatial queries + map data — handled via SIGINT
        logger.info("collector_agent.geoint_passthrough", query=query)

    return results
