"""Analytics routes — graph algorithms and anomaly detection."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from nexus.dependencies import get_neo4j, get_cache_service, get_gds_manager

logger = structlog.get_logger()
from nexus.api.middleware.rbac import require_viewer
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.graph_algorithms import GraphAlgorithms
from nexus.analytics.anomaly_detector import AnomalyDetector
from nexus.analytics.community_analyzer import CommunityAnalyzer
from nexus.analytics.temporal_analyzer import TemporalAnalyzer
from nexus.services.cache import CacheService
from nexus.services.gds_manager import GDSProjectionManager

router = APIRouter()


def _get_algorithms(driver=Depends(get_neo4j)) -> GraphAlgorithms:
    return GraphAlgorithms(Neo4jClient(driver))


@router.get("/community-detection")
async def community_detection(
    _user=Depends(require_viewer),
    algo: GraphAlgorithms = Depends(_get_algorithms),
):
    """Run Louvain community detection on the entity graph."""
    results = await algo.run_louvain()

    communities: dict[int, list] = {}
    for r in results:
        cid = r["communityId"]
        if cid not in communities:
            communities[cid] = []
        communities[cid].append(
            {"id": r["id"], "name": r["name"], "type": r["type"]}
        )

    return {
        "algorithm": "louvain",
        "communityCount": len(communities),
        "communities": communities,
    }


@router.get("/centrality")
async def centrality_analysis(
    algo_name: str = Query("pagerank", description="Algorithm: pagerank, betweenness"),
    algo: GraphAlgorithms = Depends(_get_algorithms),
):
    """Run centrality analysis on the entity graph."""
    if algo_name == "betweenness":
        results = await algo.run_betweenness_centrality()
    else:
        results = await algo.run_pagerank()

    return {
        "algorithm": algo_name,
        "results": [
            {"id": r["id"], "name": r["name"], "type": r["type"], "score": r["score"]}
            for r in results
        ],
    }


@router.get("/communities")
async def get_communities(driver=Depends(get_neo4j)):
    """Return entities grouped by their stored communityId."""
    client = Neo4jClient(driver)
    rows = await client.execute_read(
        """MATCH (e:Entity) WHERE e.communityId IS NOT NULL
           RETURN e.communityId AS community_id,
                  collect({id: e.id, name: e.name, type: e.type, riskScore: e.riskScore}) AS members,
                  count(e) AS member_count
           ORDER BY member_count DESC
           LIMIT 50""",
    )
    return [dict(r) for r in rows]


@router.get("/anomalies")
async def anomaly_detection(
    algo: GraphAlgorithms = Depends(_get_algorithms),
):
    """Detect anomalous entities based on graph structure.

    Phase 1 uses betweenness centrality outliers as a simple anomaly signal.
    Advanced ML-based anomaly detection comes in Phase 3.
    """
    results = await algo.run_betweenness_centrality()
    if not results:
        return {"anomalies": []}

    scores = [r["score"] for r in results]
    mean_score = sum(scores) / len(scores)
    std_score = (sum((s - mean_score) ** 2 for s in scores) / len(scores)) ** 0.5

    threshold = mean_score + 2 * std_score if std_score > 0 else mean_score * 2
    anomalies = [
        {"id": r["id"], "name": r["name"], "type": r["type"], "score": r["score"]}
        for r in results
        if r["score"] > threshold
    ]

    return {
        "method": "betweenness_outlier",
        "threshold": threshold,
        "anomalies": anomalies,
    }


@router.get("/anomalies/advanced")
async def advanced_anomaly_detection(
    methods: str | None = Query(None, description="Comma-separated: statistical,graph,temporal"),
    limit: int = Query(500, ge=10, le=2000),
    driver=Depends(get_neo4j),
    cache: CacheService = Depends(get_cache_service),
    gds: GDSProjectionManager = Depends(get_gds_manager),
) -> dict[str, Any]:
    """Run advanced multi-method anomaly detection."""
    cache_key = f"anomalies:{methods or 'all'}:{limit}"
    cached = await cache.get_analytics(cache_key)
    if cached is not None:
        return cached

    try:
        await gds.ensure_projection("nexus-full")

        client = Neo4jClient(driver)
        detector = AnomalyDetector(client)

        method_list = [m.strip() for m in methods.split(",")] if methods else None
        anomalies = await detector.detect_all(methods=method_list, limit=limit)

        result = {
            "method": "multi-method",
            "anomaly_count": len(anomalies),
            "anomalies": [
                {
                    "entity_id": a.entity_id,
                    "entity_name": a.entity_name,
                    "anomaly_type": a.anomaly_type,
                    "score": a.score,
                    "evidence": a.evidence,
                }
                for a in anomalies
            ],
        }
        await cache.cache_analytics(cache_key, result, ttl=60)
        return result
    except Exception as exc:
        logger.error("analytics.anomalies_advanced.failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Analytics service temporarily unavailable")


@router.get("/communities/enhanced")
async def enhanced_community_detection(
    driver=Depends(get_neo4j),
    cache: CacheService = Depends(get_cache_service),
    gds: GDSProjectionManager = Depends(get_gds_manager),
) -> dict[str, Any]:
    """Run enhanced community detection with INT composition and risk analysis."""
    cached = await cache.get_analytics("communities_enhanced")
    if cached is not None:
        return cached

    try:
        await gds.ensure_projection("nexus-community")

        client = Neo4jClient(driver)
        analyzer = CommunityAnalyzer(client)
        result = await analyzer.detect_communities_enhanced()

        await cache.cache_analytics("communities_enhanced", result, ttl=120)
        return result
    except Exception as exc:
        logger.error("analytics.communities_enhanced.failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Analytics service temporarily unavailable")


@router.get("/communities/{community_id}/details")
async def community_details(
    community_id: int,
    driver=Depends(get_neo4j),
) -> dict[str, Any]:
    """Get detailed information for a specific community."""
    client = Neo4jClient(driver)
    analyzer = CommunityAnalyzer(client)
    return await analyzer.get_community_details(community_id)


@router.get("/temporal/{entity_id}")
async def temporal_analysis(
    entity_id: str,
    driver=Depends(get_neo4j),
) -> dict[str, Any]:
    """Analyze temporal activity patterns for an entity."""
    client = Neo4jClient(driver)

    # Fetch entity events
    results = await client.execute_read(
        """
        MATCH (e {id: $entityId})-[r]-()
        WHERE r.created_at IS NOT NULL
        RETURN r.created_at AS timestamp, type(r) AS rel_type
        ORDER BY r.created_at
        """,
        {"entityId": entity_id},
    )

    events = [{"timestamp": r["timestamp"], "rel_type": r["rel_type"]} for r in results]
    analyzer = TemporalAnalyzer()

    return {
        "entity_id": entity_id,
        "activity": analyzer.analyze_activity_patterns(events),
        "periodicity": analyzer.detect_periodicity(events),
        "burstiness": analyzer.compute_burstiness(events),
    }


@router.get("/shortest-path")
async def shortest_path(
    from_id: str = Query(..., alias="from", description="Source entity ID"),
    to_id: str = Query(..., alias="to", description="Target entity ID"),
    algo: GraphAlgorithms = Depends(_get_algorithms),
):
    """Find the shortest path between two entities."""
    results = await algo.find_shortest_path(from_id, to_id)
    return {
        "from": from_id,
        "to": to_id,
        "path": [
            {"id": r["id"], "name": r["name"], "type": r["type"]}
            for r in results
        ],
        "hops": max(len(results) - 1, 0),
    }
