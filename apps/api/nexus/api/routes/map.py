"""Map data routes — spatial queries for the frontend map."""

from fastapi import APIRouter, Depends, Query

from nexus.dependencies import get_neo4j
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.repository import EntityRepository

router = APIRouter()


def _get_repository(driver=Depends(get_neo4j)) -> EntityRepository:
    return EntityRepository(Neo4jClient(driver))


@router.get("/entities")
async def get_map_entities(
    west: float = Query(..., description="Bounding box west longitude"),
    south: float = Query(..., description="Bounding box south latitude"),
    east: float = Query(..., description="Bounding box east longitude"),
    north: float = Query(..., description="Bounding box north latitude"),
    types: str | None = Query(None, description="Comma-separated entity types"),
    repo: EntityRepository = Depends(_get_repository),
):
    """Get entities within a bounding box for map display."""
    entity_types = types.split(",") if types else None
    results = await repo.get_entities_by_bbox(west, south, east, north, entity_types)
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "name": r["name"],
            "position": {"latitude": r["latitude"], "longitude": r["longitude"]},
            "confidence": r["confidence"],
            "sourceInt": r["source_int"],
            "riskScore": r.get("risk_score", 0),
            "activity": _derive_activity(r),
            "activityType": _derive_activity_type(r),
        }
        for r in results
    ]


def _derive_activity(entity: dict) -> str:
    """Derive activity string from entity type/properties."""
    etype = entity.get("type", "")
    props = entity.get("properties") or {}
    if isinstance(props, str):
        props = {}
    if etype == "Aircraft":
        return f"En route to {props.get('destination', 'N/A')}"
    elif etype == "Vessel":
        return f"Heading to {props.get('destination', 'N/A')}"
    elif etype == "IPAddress":
        return props.get("last_scan", "Monitored")
    elif etype == "ThreatActor":
        return props.get("latest_activity", "Under surveillance")
    elif etype == "SocialAccount":
        return props.get("last_post_summary", "Active")
    elif etype == "Person":
        return props.get("last_activity", "")
    elif etype == "Domain":
        return props.get("status", "")
    return ""


def _derive_activity_type(entity: dict) -> str:
    """Derive activity type from entity type."""
    etype = entity.get("type", "")
    if etype in ("Aircraft", "Vessel"):
        return "moving"
    elif etype in ("IPAddress", "Domain"):
        return "scanning"
    elif etype in ("SocialAccount", "Post", "Hashtag"):
        return "communicating"
    elif etype == "ThreatActor":
        return "alert"
    return "idle"


@router.get("/heatmap")
async def get_heatmap(
    west: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    north: float = Query(...),
    metric: str = Query("activity", description="Metric: activity, risk, confidence"),
    repo: EntityRepository = Depends(_get_repository),
):
    """Get heatmap data within a bounding box."""
    results = await repo.get_entities_by_bbox(west, south, east, north)
    weight_key = "risk_score" if metric == "risk" else "confidence"
    return [
        {
            "position": {"latitude": r["latitude"], "longitude": r["longitude"]},
            "weight": r.get(weight_key, 1.0),
        }
        for r in results
    ]


@router.get("/tracks/{entity_id}")
async def get_entity_tracks(
    entity_id: str,
    repo: EntityRepository = Depends(_get_repository),
):
    """Get movement tracks for a tracked entity (aircraft, vessel, person).

    Full track data available in Phase 2 with SIGINT collectors.
    """
    # Query for entities with temporal location data
    client = repo._client
    records = await client.execute_read(
        """
        MATCH (e:Entity {id: $id})-[:LOCATED_AT|OBSERVED_AT|DEPARTED_FROM|ARRIVED_AT]->(l:Location)
        RETURN l.coordinates.latitude AS latitude,
               l.coordinates.longitude AS longitude,
               l.name AS name
        """,
        {"id": entity_id},
    )
    return {
        "entityId": entity_id,
        "points": [
            {
                "position": {"latitude": r["latitude"], "longitude": r["longitude"]},
                "name": r.get("name", ""),
            }
            for r in records
        ],
    }


@router.get("/connections")
async def get_map_connections(
    west: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    north: float = Query(...),
    repo: EntityRepository = Depends(_get_repository),
):
    """Get entity-to-entity connections within a bounding box for connection line rendering."""
    client = repo._client
    try:
        records = await client.execute_read(
            """
            MATCH (a:Entity)-[r]-(b:Entity)
            WHERE a.longitude >= $west AND a.longitude <= $east
              AND a.latitude >= $south AND a.latitude <= $north
              AND b.longitude IS NOT NULL AND b.latitude IS NOT NULL
            RETURN a.id AS src_id, a.longitude AS src_lng, a.latitude AS src_lat, a.type AS src_type,
                   b.id AS tgt_id, b.longitude AS tgt_lng, b.latitude AS tgt_lat, b.type AS tgt_type,
                   type(r) AS rel_type, r.confidence AS confidence
            LIMIT 200
            """,
            {"west": west, "south": south, "east": east, "north": north},
        )
        return [
            {
                "source": {
                    "id": r["src_id"],
                    "longitude": r["src_lng"],
                    "latitude": r["src_lat"],
                    "type": r["src_type"],
                },
                "target": {
                    "id": r["tgt_id"],
                    "longitude": r["tgt_lng"],
                    "latitude": r["tgt_lat"],
                    "type": r["tgt_type"],
                },
                "rel_type": r["rel_type"],
                "confidence": r.get("confidence", 0.5),
            }
            for r in records
        ]
    except Exception:
        return []


@router.get("/clusters")
async def get_clusters(
    west: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    north: float = Query(...),
    zoom: int = Query(5, ge=1, le=20),
    repo: EntityRepository = Depends(_get_repository),
):
    """Get entity clusters by zoom level.

    Simple server-side clustering by grid cells.
    """
    results = await repo.get_entities_by_bbox(west, south, east, north)

    # Grid-based clustering
    cell_size = 360 / (2**zoom)
    clusters: dict[str, dict] = {}

    for r in results:
        grid_x = int(r["longitude"] / cell_size)
        grid_y = int(r["latitude"] / cell_size)
        key = f"{grid_x}:{grid_y}"

        if key not in clusters:
            clusters[key] = {
                "id": key,
                "position": {"latitude": r["latitude"], "longitude": r["longitude"]},
                "count": 0,
                "entityTypes": {},
            }
        clusters[key]["count"] += 1
        entity_type = r.get("type", "Unknown")
        clusters[key]["entityTypes"][entity_type] = (
            clusters[key]["entityTypes"].get(entity_type, 0) + 1
        )

    return list(clusters.values())
