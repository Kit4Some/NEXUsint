"""OSINT AI Chat Engine — RAG-powered conversational intelligence analyst.

Integrates: ReasoningEngine, GraphAlgorithms, AnomalyDetector, CrossIntCorrelator
with intent classification, conversation memory, and structured intelligence products.
"""

from typing import Any

import httpx
import structlog

from nexus.config import settings
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.repository import EntityRepository
from nexus.knowledge.graph_algorithms import GraphAlgorithms
from nexus.knowledge.reasoning_engine import ReasoningEngine
from nexus.analytics.anomaly_detector import AnomalyDetector

logger = structlog.get_logger()

_SYSTEM_PROMPT = """You are NEXUS AI, an elite OSINT (Open Source Intelligence) analyst assistant.
You have access to a knowledge graph containing entities (Person, Organization, IPAddress, Domain,
ThreatActor, Location, Aircraft, Vessel, SocialAccount) and their relationships.

You also have access to a real-time live intelligence feed that provides:
- Current global news with risk scoring (0-10)
- Live aircraft tracking (ADS-B) including tracked/alerted and military aircraft
- Seismic activity (USGS earthquakes)
- GPS jamming zone detection
- Defense sector stock movements and oil prices

You also have access to analytical tools:
- Entity tracking (temporal chains, location trails, extended networks)
- Relationship inference (ontology-based: PART_OF→TARGETS, ATTRIBUTED_TO→USES, etc.)
- Cross-INT correlation (temporal, spatial, graph-based across CYBINT/SOCMINT/SIGINT/GEOINT)
- Anomaly detection (statistical outliers, graph structural, temporal spikes)
- Graph algorithms (PageRank centrality, community detection, shortest paths)

When answering questions:
- Reference specific entities by name, type, and ID
- Cite confidence scores and source intelligence types (CYBINT, SOCMINT, SIGINT, GEOINT)
- Highlight risk scores and threat levels
- When appropriate, produce structured intelligence products:
  * THREAT ASSESSMENT: threat level, indicators, TTPs, recommended actions
  * LINK ANALYSIS: key connections, shortest paths, bridge entities
  * PATTERN ANALYSIS: temporal patterns, anomalies, behavioral indicators
- Suggest follow-up investigation actions with specific entity IDs
- Be precise, analytical, and concise
- Always indicate confidence in your assessments

If the context doesn't contain the answer, say so and suggest what collection or investigation
could fill the gap."""

# Intent classification keywords
_INTENT_PATTERNS: dict[str, list[str]] = {
    "track": ["track", "tracking", "trail", "location history", "movement", "where has", "traveled", "추적", "이동"],
    "correlate": ["correlat", "connection", "link between", "relationship between", "connected to", "associated", "상관", "연관"],
    "threat": ["threat", "risk", "danger", "malicious", "attack", "campaign", "apt", "ttp", "위협", "위험"],
    "anomaly": ["anomal", "unusual", "outlier", "suspicious", "unexpected", "abnormal", "이상", "비정상"],
    "centrality": ["important", "central", "influential", "key player", "hub", "bridge", "중요", "핵심"],
    "community": ["group", "cluster", "community", "network", "gang", "organization", "커뮤니티", "그룹", "조직"],
    "infer": ["infer", "predict", "likely", "probable", "might be", "could be", "implicit", "추론", "예측"],
    "summarize": ["summary", "summarize", "overview", "brief", "what do we know", "요약", "개요"],
    "collect": ["collect", "scan", "gather", "수집", "스캔", "수집해", "검색해"],
    "investigate": ["investigate", "create investigation", "조사", "수사", "분석해"],
    "graph_query": ["connections of", "neighbors", "shortest path", "path between", "그래프", "연결", "경로"],
    "history": ["history", "이력", "과거", "최근 수집", "작업 목록", "what was collected", "recent jobs", "past scans"],
    "status": ["status", "상태", "진행", "running", "어디까지", "progress", "active jobs", "진행중"],
}


class ConversationMemory:
    """Simple in-memory conversation history per session."""

    def __init__(self, max_turns: int = 10):
        self._max_turns = max_turns
        self._history: list[dict[str, str]] = []

    def add_user(self, message: str) -> None:
        self._history.append({"role": "user", "content": message})
        self._trim()

    def add_assistant(self, message: str) -> None:
        self._history.append({"role": "assistant", "content": message})
        self._trim()

    def get_history(self) -> list[dict[str, str]]:
        return list(self._history)

    def _trim(self) -> None:
        max_msgs = self._max_turns * 2
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]


# Session-based conversation memories
_memories: dict[str, ConversationMemory] = {}


def _get_memory(session_id: str) -> ConversationMemory:
    if session_id not in _memories:
        _memories[session_id] = ConversationMemory()
    # Cap total sessions to prevent memory leak
    if len(_memories) > 200:
        oldest = list(_memories.keys())[0]
        del _memories[oldest]
    return _memories[session_id]


class ChatEngine:
    """RAG-powered chat engine with analytical tool integration."""

    def __init__(self, client: Neo4jClient, pg_pool=None) -> None:
        self._client = client
        self._pg_pool = pg_pool
        self._repo = EntityRepository(client)
        self._algo = GraphAlgorithms(client)
        self._reasoning = ReasoningEngine(client)

    async def process_message(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Process a user message and return AI response with context."""
        memory = _get_memory(session_id)
        memory.add_user(message)

        # 1. Classify intent
        intents = self._classify_intent(message)

        # 2. Retrieve relevant entities from knowledge graph
        retrieved = await self._retrieve_context(message, context)

        # 3. Run analytical tools based on intent
        analysis = await self._run_analysis(intents, retrieved, context)

        # 4. Build prompt with context + analysis + history
        prompt = self._build_prompt(message, retrieved, analysis, memory)

        # 5. Call LLM
        response_text = await self._call_llm(prompt)

        # 6. Generate suggested actions
        referenced = retrieved.get("entities", [])
        actions = self._generate_actions(intents, referenced, analysis, message)

        memory.add_assistant(response_text)

        return {
            "response": response_text,
            "entities": referenced[:15],
            "actions": actions,
            "context_used": {
                "entity_count": len(referenced),
                "relationship_count": len(retrieved.get("relationships", [])),
                "intents": intents,
                "analysis_performed": list(analysis.keys()),
            },
        }

    # -----------------------------------------------------------------
    # Intent classification
    # -----------------------------------------------------------------

    def _classify_intent(self, message: str) -> list[str]:
        msg_lower = message.lower()
        intents = [
            intent for intent, keywords in _INTENT_PATTERNS.items()
            if any(kw in msg_lower for kw in keywords)
        ]
        return intents or ["summarize"]

    # -----------------------------------------------------------------
    # Context retrieval
    # -----------------------------------------------------------------

    async def _retrieve_context(
        self, message: str, context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entities: list[dict] = []
        relationships: list[dict] = []

        # Fetch neighborhood of context entity
        entity_id = None
        if context:
            entity_id = context.get("entity_id") or context.get("entityId")
        if entity_id:
            try:
                rows = await self._client.execute_read(
                    """
                    MATCH (e:Entity {id: $id})-[r]-(related:Entity)
                    RETURN e.id AS eid, e.name AS ename, e.type AS etype,
                           e.confidence AS econf, e.riskScore AS erisk,
                           e.sourceInt AS esrc,
                           type(r) AS rel_type, r.confidence AS rel_conf,
                           related.id AS rid, related.name AS rname,
                           related.type AS rtype, related.riskScore AS rrisk,
                           related.sourceInt AS rsrc
                    LIMIT 40
                    """,
                    {"id": entity_id},
                )
                for row in rows:
                    entities.append({
                        "id": row["eid"], "name": row["ename"], "type": row["etype"],
                        "confidence": row["econf"], "riskScore": row["erisk"],
                        "sourceInt": row["esrc"],
                    })
                    entities.append({
                        "id": row["rid"], "name": row["rname"], "type": row["rtype"],
                        "riskScore": row.get("rrisk", 0), "sourceInt": row.get("rsrc", ""),
                    })
                    relationships.append({
                        "source": row["ename"], "target": row["rname"],
                        "type": row["rel_type"], "confidence": row.get("rel_conf", 0),
                    })
            except Exception as exc:
                logger.warning("chat.context_fetch_failed", error=str(exc))

        # Keyword search
        keywords = [w for w in message.split() if len(w) > 2]
        search_q = " ".join(keywords[:5])
        if search_q:
            try:
                results = await self._client.execute_read(
                    """
                    MATCH (e:Entity)
                    WHERE toLower(e.name) CONTAINS toLower($q)
                       OR toLower(e.type) CONTAINS toLower($q)
                    RETURN e.id AS id, e.name AS name, e.type AS type,
                           e.confidence AS confidence, e.riskScore AS riskScore,
                           e.sourceInt AS sourceInt
                    LIMIT 15
                    """,
                    {"q": search_q},
                )
                for row in results:
                    entities.append(dict(row))
            except Exception:
                pass

        for kw in keywords[:3]:
            if len(kw) < 3:
                continue
            try:
                results = await self._client.execute_read(
                    """
                    MATCH (e:Entity)
                    WHERE toLower(e.name) CONTAINS toLower($q)
                    RETURN e.id AS id, e.name AS name, e.type AS type,
                           e.confidence AS confidence, e.riskScore AS riskScore,
                           e.sourceInt AS sourceInt
                    LIMIT 5
                    """,
                    {"q": kw},
                )
                for row in results:
                    entities.append(dict(row))
            except Exception:
                pass

        # Deduplicate
        seen: set[str] = set()
        unique: list[dict] = []
        for e in entities:
            eid = e.get("id")
            if eid and eid not in seen:
                seen.add(eid)
                unique.append(e)

        # Enrich with live feed context (Redis)
        live_context = await self._retrieve_live_context(message)

        return {
            "entities": unique,
            "relationships": relationships,
            "live_feed": live_context,
        }

    async def _retrieve_live_context(self, message: str) -> dict[str, Any]:
        """Retrieve real-time live feed data from Redis for RAG context.

        Injects current intelligence situation into the AI analyst's context:
        - Recent high-risk news articles
        - Active tracked aircraft
        - Significant earthquakes
        - GPS jamming zones
        - Live feed health status
        """
        live: dict[str, Any] = {}
        msg_lower = message.lower()

        try:
            from nexus.services.live_store import get_live_data, get_timestamps

            # Always include live feed status
            timestamps = await get_timestamps()
            if timestamps:
                live["source_freshness"] = timestamps

            # Include news if query mentions news, threat, event, situation
            news_keywords = ["news", "threat", "event", "situation", "crisis",
                             "뉴스", "위협", "상황", "사건", "위기", "현재"]
            if any(kw in msg_lower for kw in news_keywords):
                news = await get_live_data("news")
                if news:
                    # Only top 10 highest-risk articles
                    top_news = sorted(news, key=lambda n: n.get("risk_score", 0), reverse=True)[:10]
                    live["current_news"] = [
                        {
                            "title": n.get("title", ""),
                            "source": n.get("source", ""),
                            "risk_score": n.get("risk_score", 0),
                            "coords": n.get("coords"),
                        }
                        for n in top_news
                    ]

            # Include flights if query mentions aircraft, flight, aviation, tracking
            flight_keywords = ["flight", "aircraft", "plane", "aviation", "tracked",
                               "항공", "비행", "추적", "항공기", "military"]
            if any(kw in msg_lower for kw in flight_keywords):
                tracked = await get_live_data("tracked_flights")
                if tracked:
                    live["tracked_aircraft"] = [
                        {
                            "callsign": f.get("callsign", ""),
                            "icao24": f.get("icao24", ""),
                            "alert_category": f.get("alert_category", ""),
                            "alert_operator": f.get("alert_operator", ""),
                            "country": f.get("country", ""),
                            "lat": f.get("lat"),
                            "lng": f.get("lng"),
                        }
                        for f in tracked[:20]
                    ]

                military = await get_live_data("military_flights")
                if military:
                    live["military_aircraft_count"] = len(military)

            # Include earthquakes if query mentions earthquake, seismic, natural disaster
            quake_keywords = ["earthquake", "seismic", "quake", "지진", "재해"]
            if any(kw in msg_lower for kw in quake_keywords):
                quakes = await get_live_data("earthquakes")
                if quakes:
                    live["recent_earthquakes"] = [
                        {"mag": q.get("mag"), "place": q.get("place"), "lat": q.get("lat"), "lng": q.get("lng")}
                        for q in quakes[:10]
                    ]

            # Include GPS jamming if query mentions jamming, gps, signal
            jamming_keywords = ["jamming", "gps", "signal", "재밍", "신호"]
            if any(kw in msg_lower for kw in jamming_keywords):
                jamming = await get_live_data("gps_jamming")
                if jamming:
                    live["gps_jamming_zones"] = jamming[:10]

        except Exception as exc:
            logger.debug("chat.live_context_failed", error=str(exc))

        return live

    # -----------------------------------------------------------------
    # Analytical tools
    # -----------------------------------------------------------------

    async def _run_analysis(
        self, intents: list[str], retrieved: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        results: dict[str, Any] = {}
        entity_ids = [e["id"] for e in retrieved.get("entities", []) if e.get("id")]
        entity_id = None
        if context:
            entity_id = context.get("entity_id") or context.get("entityId")
        if not entity_id and entity_ids:
            entity_id = entity_ids[0]

        try:
            if "track" in intents and entity_id:
                results["tracking"] = await self._reasoning.track_entity(entity_id)

            if "infer" in intents and entity_id:
                results["inferences"] = await self._reasoning.infer_relationships(entity_id)

            if "correlate" in intents and len(entity_ids) >= 2:
                results["correlations"] = await self._reasoning.correlate_entities(
                    entity_ids[:5]
                )

            if "anomaly" in intents:
                detector = AnomalyDetector(self._client)
                anomalies = await detector.detect_all(limit=100)
                results["anomalies"] = [
                    {
                        "entityId": a.entity_id, "entityName": a.entity_name,
                        "type": a.anomaly_type, "score": a.score,
                        "evidence": a.evidence,
                    }
                    for a in anomalies[:10]
                ]

            if "centrality" in intents:
                top_nodes = await self._algo.run_pagerank()
                results["centrality"] = top_nodes[:10]

            if "community" in intents:
                communities = await self._algo.run_louvain()
                results["communities"] = communities[:10]

            if "graph_query" in intents and len(entity_ids) >= 2:
                try:
                    path_rows = await self._client.execute_read(
                        """
                        MATCH p = shortestPath((a:Entity {id: $from_id})-[*..6]-(b:Entity {id: $to_id}))
                        UNWIND nodes(p) AS n
                        RETURN n.id AS id, n.name AS name, n.type AS type
                        """,
                        {"from_id": entity_ids[0], "to_id": entity_ids[1]},
                    )
                    results["shortest_path"] = [dict(r) for r in path_rows]
                except Exception:
                    results["shortest_path"] = []

            if "threat" in intents and entity_ids:
                # Fetch high-risk entities in the neighborhood
                high_risk = [
                    e for e in retrieved.get("entities", [])
                    if (e.get("riskScore") or 0) >= 5
                ]
                results["high_risk_entities"] = high_risk[:10]

            if "history" in intents:
                results["collection_history"] = await self._query_collection_history()

            if "status" in intents:
                results["active_jobs"] = await self._query_active_jobs()

        except Exception as exc:
            logger.warning("chat.analysis_failed", error=str(exc))

        return results

    async def _query_collection_history(self, limit: int = 10) -> list[dict]:
        """Query recent collection jobs from PostgreSQL."""
        if not self._pg_pool:
            return []
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT id, int_type, query, scan_type, status, result_count,
                              created_at, completed_at
                       FROM collection_jobs ORDER BY created_at DESC LIMIT $1""",
                    limit,
                )
                return [
                    {
                        "id": str(r["id"]),
                        "int_type": r["int_type"],
                        "query": r["query"],
                        "scan_type": r["scan_type"],
                        "status": r["status"],
                        "result_count": r["result_count"],
                        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                        "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                    }
                    for r in rows
                ]
        except Exception as exc:
            logger.warning("chat.history_query_failed", error=str(exc))
            return []

    async def _query_active_jobs(self) -> list[dict]:
        """Query currently running/queued collection jobs from PostgreSQL."""
        if not self._pg_pool:
            return []
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT id, int_type, query, scan_type, status, progress, result_count
                       FROM collection_jobs WHERE status IN ('queued', 'running')
                       ORDER BY created_at DESC LIMIT 10"""
                )
                return [
                    {
                        "id": str(r["id"]),
                        "int_type": r["int_type"],
                        "query": r["query"],
                        "scan_type": r["scan_type"],
                        "status": r["status"],
                        "progress": r["progress"],
                        "result_count": r["result_count"],
                    }
                    for r in rows
                ]
        except Exception as exc:
            logger.warning("chat.active_jobs_query_failed", error=str(exc))
            return []

    # -----------------------------------------------------------------
    # Prompt building
    # -----------------------------------------------------------------

    def _build_prompt(
        self, message: str, retrieved: dict[str, Any],
        analysis: dict[str, Any], memory: ConversationMemory,
    ) -> list[dict[str, str]]:
        context_parts: list[str] = []

        # Entities
        entities = retrieved.get("entities", [])
        if entities:
            context_parts.append("=== ENTITIES IN KNOWLEDGE GRAPH ===")
            for e in entities[:20]:
                line = f"- [{e.get('type', '?')}] {e.get('name', '?')} (id:{e.get('id', '?')})"
                if e.get("confidence"):
                    line += f" conf:{e['confidence']:.0%}"
                if e.get("riskScore"):
                    line += f" risk:{e['riskScore']}/10"
                if e.get("sourceInt"):
                    line += f" [{e['sourceInt']}]"
                context_parts.append(line)

        # Relationships
        rels = retrieved.get("relationships", [])
        if rels:
            context_parts.append("\n=== RELATIONSHIPS ===")
            for r in rels[:20]:
                line = f"- {r.get('source', '?')} --[{r.get('type', '?')}]--> {r.get('target', '?')}"
                if r.get("confidence"):
                    line += f" (conf:{r['confidence']:.0%})"
                context_parts.append(line)

        # Analytical results
        if analysis.get("tracking"):
            t = analysis["tracking"]
            context_parts.append("\n=== TRACKING CHAIN ===")
            entity_info = t.get("entity", {})
            context_parts.append(f"Entity: {entity_info.get('name')} ({entity_info.get('type')})")
            context_parts.append(f"Connections: {t.get('totalConnections', 0)}, Locations: {t.get('totalLocations', 0)}")
            for loc in t.get("locationTrail", [])[:5]:
                context_parts.append(f"  Location: {loc.get('locationName')} ({loc.get('latitude')}, {loc.get('longitude')})")
            context_parts.append(f"INT breakdown: {t.get('intSourceBreakdown', {})}")

        if analysis.get("inferences"):
            inf = analysis["inferences"]
            context_parts.append("\n=== INFERRED RELATIONSHIPS ===")
            for i in inf.get("inferences", [])[:8]:
                context_parts.append(
                    f"  {i.get('source_name', '?')} --[{i.get('inferred_type', '?')}]--> "
                    f"{i.get('target_name', '?')} (conf:{i.get('confidence', 0):.0%}, rule:{i.get('rule', '?')})"
                )

        if analysis.get("correlations"):
            corr = analysis["correlations"]
            context_parts.append("\n=== ENTITY CORRELATIONS ===")
            for sn in corr.get("shared_neighbors", [])[:5]:
                context_parts.append(f"  Shared neighbor: {sn.get('name')} ({sn.get('type')})")
            for path in corr.get("paths", [])[:3]:
                context_parts.append(f"  Path: {' → '.join(str(n) for n in path.get('nodes', []))}")

        if analysis.get("anomalies"):
            context_parts.append("\n=== DETECTED ANOMALIES ===")
            for a in analysis["anomalies"][:8]:
                context_parts.append(
                    f"  [{a['type']}] {a['entityName']} (score:{a['score']:.2f})"
                )

        if analysis.get("centrality"):
            context_parts.append("\n=== TOP CENTRAL NODES (PageRank) ===")
            for c in analysis["centrality"][:5]:
                context_parts.append(f"  {c.get('name', '?')} ({c.get('type', '?')}) score:{c.get('score', 0):.4f}")

        if analysis.get("communities"):
            context_parts.append("\n=== COMMUNITIES (Louvain) ===")
            for comm in analysis["communities"][:5]:
                context_parts.append(f"  Community {comm.get('community_id', '?')}: {comm.get('member_count', 0)} members")

        if analysis.get("high_risk_entities"):
            context_parts.append("\n=== HIGH RISK ENTITIES ===")
            for hr in analysis["high_risk_entities"]:
                context_parts.append(f"  [{hr.get('type')}] {hr.get('name')} risk:{hr.get('riskScore')}/10 [{hr.get('sourceInt', '')}]")

        if analysis.get("collection_history"):
            context_parts.append("\n=== RECENT COLLECTION HISTORY ===")
            for job in analysis["collection_history"]:
                context_parts.append(
                    f"  [{job['int_type']}] {job['query']} ({job['scan_type']}) "
                    f"status:{job['status']} results:{job['result_count']} "
                    f"at:{job['created_at']}"
                )

        if analysis.get("active_jobs"):
            context_parts.append("\n=== ACTIVE COLLECTION JOBS ===")
            for job in analysis["active_jobs"]:
                context_parts.append(
                    f"  [{job['int_type']}] {job['query']} ({job['scan_type']}) "
                    f"status:{job['status']} progress:{job['progress']}% "
                    f"results:{job['result_count']}"
                )

        # Live feed real-time context
        live = retrieved.get("live_feed", {})
        if live:
            if live.get("current_news"):
                context_parts.append("\n=== LIVE INTELLIGENCE FEED (Real-time) ===")
                for n in live["current_news"]:
                    context_parts.append(
                        f"  [NEWS risk:{n['risk_score']}/10] {n['title']} (via {n['source']})"
                    )
            if live.get("tracked_aircraft"):
                context_parts.append("\n=== TRACKED AIRCRAFT (Live ADS-B) ===")
                for a in live["tracked_aircraft"]:
                    parts = [f"{a['callsign']}"]
                    if a.get("alert_category"):
                        parts.append(f"alert:{a['alert_category']}")
                    if a.get("alert_operator"):
                        parts.append(f"op:{a['alert_operator']}")
                    if a.get("country"):
                        parts.append(f"country:{a['country']}")
                    context_parts.append(f"  {' | '.join(parts)}")
            if live.get("military_aircraft_count"):
                context_parts.append(f"\n  [SIGINT] {live['military_aircraft_count']} military aircraft currently tracked")
            if live.get("recent_earthquakes"):
                context_parts.append("\n=== SEISMIC ACTIVITY (Live USGS) ===")
                for q in live["recent_earthquakes"]:
                    context_parts.append(f"  M{q['mag']:.1f} — {q['place']}")
            if live.get("gps_jamming_zones"):
                context_parts.append(f"\n  [SIGINT] {len(live['gps_jamming_zones'])} GPS jamming zones detected")

        context_text = "\n".join(context_parts) if context_parts else "No relevant entities found in the knowledge graph."

        # Build messages: system + history + current
        messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
        messages.extend(memory.get_history()[:-1])  # history minus last (which is current message)
        messages.append({
            "role": "user",
            "content": f"Knowledge Graph Context:\n{context_text}\n\nUser Question: {message}",
        })
        return messages

    # -----------------------------------------------------------------
    # LLM call
    # -----------------------------------------------------------------

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        api_key = settings.openai_api_key
        if not api_key:
            return self._fallback_response(messages)

        model = settings.llm_model or "gpt-4o-mini"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": settings.llm_temperature,
                        "max_tokens": 2048,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.error("chat.llm_call_failed", error=str(exc))
            return self._fallback_response(messages)

    def _fallback_response(self, messages: list[dict[str, str]]) -> str:
        """Generate a context-based response without LLM."""
        user_msg = messages[-1]["content"] if messages else ""
        lines = user_msg.split("\n")
        entity_lines = [ln for ln in lines if ln.startswith("- [")]
        analysis_lines = [ln for ln in lines if ln.startswith("  ")]

        if not entity_lines and not analysis_lines:
            return (
                "I found no matching entities in the knowledge graph for your query. "
                "Try running an OSINT collection to populate the knowledge graph, "
                "or load demo data from the Dashboard."
            )

        response = "Based on the knowledge graph analysis:\n\n"
        if entity_lines:
            response += "**Entities:**\n"
            for line in entity_lines[:10]:
                response += f"{line}\n"

        rel_lines = [ln for ln in lines if ln.startswith("- ") and "--[" in ln]
        if rel_lines:
            response += "\n**Relationships:**\n"
            for line in rel_lines[:10]:
                response += f"{line}\n"

        if analysis_lines:
            response += "\n**Analysis:**\n"
            for line in analysis_lines[:15]:
                response += f"{line}\n"

        response += (
            "\n\n*Note: LLM API key is not configured. Set `OPENAI_API_KEY` "
            "for AI-powered analysis and reasoning.*"
        )
        return response

    # -----------------------------------------------------------------
    # Action generation
    # -----------------------------------------------------------------

    def _generate_actions(
        self, intents: list[str], entities: list[dict],
        analysis: dict[str, Any],
        message: str = "",
    ) -> list[dict[str, Any]]:
        """Generate suggested follow-up actions based on intent and results."""
        actions: list[dict[str, Any]] = []
        first_id = entities[0]["id"] if entities else None
        entity_ids = [e["id"] for e in entities if e.get("id")]

        if "track" not in intents and first_id:
            actions.append({
                "type": "track",
                "label": "추적 체인 분석",
                "params": {"entity_id": first_id},
            })

        if "anomaly" not in intents:
            actions.append({
                "type": "anomaly",
                "label": "이상 탐지 실행",
                "params": {},
            })

        if "centrality" not in intents:
            actions.append({
                "type": "centrality",
                "label": "핵심 노드 분석",
                "params": {},
            })

        if "infer" not in intents and first_id:
            actions.append({
                "type": "infer",
                "label": "관계 추론",
                "params": {"entity_id": first_id},
            })

        if len(entities) >= 2 and "correlate" not in intents:
            actions.append({
                "type": "correlate",
                "label": "상관분석",
                "params": {"entity_ids": [e["id"] for e in entities[:3]]},
            })

        if analysis.get("high_risk_entities"):
            actions.append({
                "type": "investigate",
                "label": "고위험 엔티티 조사",
                "params": {"entity_id": analysis["high_risk_entities"][0].get("id")},
            })

        # --- Extended intents: collect, investigate, graph_query ---

        if "collect" in intents:
            int_type = "CYBINT"
            scan_type = "basic"
            msg_lower = message.lower()
            if any(k in msg_lower for k in ["social", "twitter", "소셜", "sns"]):
                int_type = "SOCMINT"
                scan_type = "username"
            elif any(k in msg_lower for k in ["ip", "domain", "cyber", "사이버"]):
                int_type = "CYBINT"
                scan_type = "ip_lookup"
            elif any(k in msg_lower for k in ["signal", "flight", "vessel", "신호"]):
                int_type = "SIGINT"
                scan_type = "flights"
            elif any(k in msg_lower for k in ["satellite", "geo", "위성", "지리"]):
                int_type = "GEOINT"
                scan_type = "satellite"

            collect_query = entities[0]["name"] if entities else message.split()[-1]
            actions.append({
                "type": "TRIGGER_COLLECTION",
                "label": f"Collect {int_type}: {collect_query[:30]}",
                "params": {
                    "int_type": int_type,
                    "query": collect_query,
                    "scan_type": scan_type,
                },
            })

        if "investigate" in intents and first_id:
            actions.append({
                "type": "CREATE_INVESTIGATION",
                "label": f"Investigate: {entities[0]['name'][:20] if entities else 'target'}",
                "params": {
                    "query": f"Investigate {entities[0]['name'] if entities else 'target'}",
                    "target_ints": [entities[0].get("sourceInt", "CYBINT")] if entities else ["CYBINT"],
                    "entity_id": first_id,
                },
            })

        if "graph_query" in intents and len(entity_ids) >= 2:
            actions.append({
                "type": "SHOW_SHORTEST_PATH",
                "label": f"Path: {entities[0]['name'][:12]} → {entities[1]['name'][:12]}",
                "params": {
                    "from_id": entity_ids[0],
                    "to_id": entity_ids[1],
                },
            })

        # FLY_TO for first entity with location
        for e in entities[:5]:
            lat = e.get("latitude")
            lng = e.get("longitude")
            if lat and lng:
                actions.append({
                    "type": "FLY_TO_TARGET",
                    "label": f"Locate {e['name'][:20]}",
                    "params": {"entityId": e["id"], "latitude": lat, "longitude": lng},
                })
                break

        return actions[:6]
