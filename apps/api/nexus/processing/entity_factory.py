"""Convert NER extraction results and collection results to POLE-compatible entity models."""

from typing import Any

from nexus.processing.ner import NEREntity
from nexus.models.entity import EntityCreate, EntityType

# NER label → EntityType mapping
LABEL_TO_TYPE: dict[str, EntityType] = {
    "Person": EntityType.Person,
    "Organization": EntityType.Organization,
    "Location": EntityType.Location,
    "Event": EntityType.Event,
    "Object": EntityType.Object,
    "IPAddress": EntityType.IPAddress,
    "Domain": EntityType.Domain,
    "Vulnerability": EntityType.Vulnerability,
    "Hash": EntityType.Indicator,
    "Email": EntityType.Indicator,
    "URL": EntityType.Indicator,
    "CryptoWallet": EntityType.Indicator,
    "Vessel": EntityType.Vessel,
    "Aircraft": EntityType.Aircraft,
    "PhoneNumber": EntityType.Indicator,
}


def ner_to_entity(ner_entity: NEREntity, source_int: str = "CYBINT") -> EntityCreate | None:
    """Convert a NER entity to an EntityCreate model.

    Returns None for entity types we don't track (Date, Time, Group, Financial).
    """
    entity_type = LABEL_TO_TYPE.get(ner_entity.label)
    if entity_type is None:
        return None

    return EntityCreate(
        name=ner_entity.text,
        type=entity_type,
        properties={
            "ner_label": ner_entity.label,
            "ner_tier": ner_entity.tier,
            "source_text_offset": f"{ner_entity.start}:{ner_entity.end}",
            "extraction_source": ner_entity.source,
        },
        confidence=ner_entity.confidence,
        source_int=source_int,
    )


def ner_batch_to_entities(
    ner_entities: list[NEREntity],
    source_int: str = "CYBINT",
) -> list[EntityCreate]:
    """Convert a batch of NER entities to EntityCreate models, filtering non-trackable types."""
    entities = []
    seen_names: set[str] = set()

    for ner_ent in ner_entities:
        entity = ner_to_entity(ner_ent, source_int)
        if entity and entity.name not in seen_names:
            entities.append(entity)
            seen_names.add(entity.name)

    return entities


# ---------------------------------------------------------------------------
# CollectionResult.normalized → EntityCreate conversion
# ---------------------------------------------------------------------------

NORMALIZED_TYPE_MAP: dict[str, EntityType] = {
    "IPAddress": EntityType.IPAddress,
    "Domain": EntityType.Domain,
    "Certificate": EntityType.Certificate,
    "ThreatActor": EntityType.ThreatActor,
    "Malware": EntityType.Malware,
    "Vulnerability": EntityType.Vulnerability,
    "Indicator": EntityType.Indicator,
    "Person": EntityType.Person,
    "Organization": EntityType.Organization,
    "Location": EntityType.Location,
    "SocialAccount": EntityType.SocialAccount,
    "Post": EntityType.Post,
    "Hashtag": EntityType.Hashtag,
    "Aircraft": EntityType.Aircraft,
    "Vessel": EntityType.Vessel,
    "FlightPath": EntityType.FlightPath,
    "VoyageTrack": EntityType.VoyageTrack,
    "SatelliteImage": EntityType.SatelliteImage,
    "GeoFeature": EntityType.GeoFeature,
}

# Entity type → candidate name fields (tried in order)
_NAME_FIELDS: dict[str, list[str]] = {
    "IPAddress": ["address", "ip", "name"],
    "Domain": ["name", "domain"],
    "Certificate": ["subject", "name"],
    "Aircraft": ["callsign", "icao24", "name"],
    "Vessel": ["name", "mmsi"],
    "FlightPath": ["callsign", "icao24"],
    "VoyageTrack": ["name", "mmsi"],
    "SocialAccount": ["username", "screen_name", "name"],
    "Post": ["id", "text"],
    "Hashtag": ["tag", "name"],
    "SatelliteImage": ["title", "name", "id"],
    "GeoFeature": ["name", "tags"],
    "Event": ["title", "name", "place", "event_type"],
}


# ---------------------------------------------------------------------------
# Live Feed → EntityCreate conversion
# ---------------------------------------------------------------------------

def live_flight_to_entities(flight: dict[str, Any]) -> list[EntityCreate]:
    """Convert a live feed flight dict to Neo4j Aircraft + Location entities.

    Creates:
      - 1 Aircraft entity (from the flight itself)
      - 0-2 Location entities (origin, destination airports if route known)
    Also returns inferred relationships between them.
    """
    callsign = flight.get("callsign") or flight.get("icao24", "")
    if not callsign:
        return []

    lat = flight.get("lat")
    lng = flight.get("lng")

    props: dict[str, Any] = {
        "icao24": flight.get("icao24", ""),
        "registration": flight.get("registration", ""),
        "model": flight.get("model", ""),
        "country": flight.get("country", ""),
        "altitude_m": flight.get("alt"),
        "speed_knots": flight.get("speed_knots"),
        "heading": flight.get("heading"),
        "squawk": flight.get("squawk", ""),
        "aircraft_category": flight.get("aircraft_category", "plane"),
        "flight_type": flight.get("type", "commercial_flight"),
        "collector": "live_feed_adsb",
        "source": "live_feed",
    }

    # Plane Alert enrichment
    for k in ("alert_category", "alert_operator", "alert_special", "alert_flag"):
        if flight.get(k):
            props[k] = flight[k]

    # Route info
    if flight.get("origin_name"):
        props["origin"] = flight["origin_name"]
    if flight.get("dest_name"):
        props["destination"] = flight["dest_name"]

    risk = 0.0
    if flight.get("alert_category"):
        risk = 7.0
    elif flight.get("type") == "military_flight":
        risk = 5.0
    elif flight.get("holding"):
        risk = 3.0

    entities: list[EntityCreate] = [
        EntityCreate(
            name=callsign,
            type=EntityType.Aircraft,
            properties=props,
            confidence=0.85,
            source_int="SIGINT",
            risk_score=risk,
            latitude=float(lat) if lat else None,
            longitude=float(lng) if lng else None,
        )
    ]

    # Origin location
    if flight.get("origin_loc") and flight.get("origin_name"):
        entities.append(EntityCreate(
            name=flight["origin_name"],
            type=EntityType.Location,
            properties={
                "locationType": "airport",
                "collector": "live_feed_adsb",
            },
            confidence=0.90,
            source_int="SIGINT",
            latitude=float(flight["origin_loc"][1]) if len(flight["origin_loc"]) > 1 else None,
            longitude=float(flight["origin_loc"][0]) if flight["origin_loc"] else None,
        ))

    # Destination location
    if flight.get("dest_loc") and flight.get("dest_name"):
        entities.append(EntityCreate(
            name=flight["dest_name"],
            type=EntityType.Location,
            properties={
                "locationType": "airport",
                "collector": "live_feed_adsb",
            },
            confidence=0.90,
            source_int="SIGINT",
            latitude=float(flight["dest_loc"][1]) if len(flight["dest_loc"]) > 1 else None,
            longitude=float(flight["dest_loc"][0]) if flight["dest_loc"] else None,
        ))

    return entities


def live_news_to_entity(article: dict[str, Any]) -> list[EntityCreate]:
    """Convert a live feed news article to a Neo4j Event entity + Location.

    High-risk news (risk_score >= 6) gets persisted to the knowledge graph
    as Event entities with OCCURRED_AT relationships to geocoded Locations.
    """
    title = article.get("title", "")
    if not title:
        return []

    coords = article.get("coords")
    lat = float(coords[0]) if coords and len(coords) >= 2 and coords[0] is not None else None
    lng = float(coords[1]) if coords and len(coords) >= 2 and coords[1] is not None else None

    risk = float(article.get("risk_score", 0))

    entities: list[EntityCreate] = [
        EntityCreate(
            name=title[:200],
            type=EntityType.Event,
            properties={
                "eventType": "NEWS_REPORT",
                "source": article.get("source", ""),
                "link": article.get("link", ""),
                "published": article.get("published", ""),
                "risk_score_raw": article.get("risk_score", 0),
                "cluster_count": article.get("cluster_count", 1),
                "collector": "live_feed_news",
            },
            confidence=min(0.5 + risk * 0.05, 0.95),
            source_int="OSINT",
            risk_score=risk,
            latitude=lat,
            longitude=lng,
        )
    ]

    # Create Location entity for geocoded articles
    if lat is not None and lng is not None:
        # Derive location name from coordinates or article source
        source_name = article.get("source", "Unknown")
        loc_name = f"News Region ({source_name})"
        entities.append(EntityCreate(
            name=loc_name,
            type=EntityType.Location,
            properties={
                "locationType": "news_region",
                "collector": "live_feed_news",
            },
            confidence=0.60,
            source_int="OSINT",
            latitude=lat,
            longitude=lng,
        ))

    return entities


def live_earthquake_to_entity(quake: dict[str, Any]) -> list[EntityCreate]:
    """Convert a USGS earthquake to a Neo4j Event entity + Location."""
    place = quake.get("place", "Unknown Location")
    mag = float(quake.get("mag", 0))

    risk = min(mag * 1.2, 10.0)

    entities: list[EntityCreate] = [
        EntityCreate(
            name=f"M{mag:.1f} Earthquake - {place}",
            type=EntityType.Event,
            properties={
                "eventType": "EARTHQUAKE",
                "magnitude": mag,
                "depth_km": quake.get("depth", 0),
                "usgs_id": quake.get("id", ""),
                "place": place,
                "collector": "live_feed_usgs",
            },
            confidence=0.95,
            source_int="GEOINT",
            risk_score=risk,
            latitude=float(quake.get("lat", 0)),
            longitude=float(quake.get("lng", 0)),
        ),
        EntityCreate(
            name=place,
            type=EntityType.Location,
            properties={
                "locationType": "seismic_zone",
                "collector": "live_feed_usgs",
            },
            confidence=0.95,
            source_int="GEOINT",
            latitude=float(quake.get("lat", 0)),
            longitude=float(quake.get("lng", 0)),
        ),
    ]
    return entities


def infer_live_relationships(
    entities: list[EntityCreate],
) -> list[dict[str, str]]:
    """Infer relationships between live feed entities.

    Aircraft → LOCATED_AT → Location (origin/destination)
    Event → OCCURRED_AT → Location
    """
    rels: list[dict[str, str]] = []
    primary = entities[0] if entities else None
    if not primary:
        return rels

    for sec in entities[1:]:
        if sec.type == EntityType.Location:
            if primary.type == EntityType.Aircraft:
                # Check if origin or destination
                origin_name = primary.properties.get("origin", "")
                if sec.name == origin_name:
                    rel_type = "ORIGINATES_FROM"
                else:
                    rel_type = "TERMINATES_AT"
                rels.append({
                    "source_name": primary.name,
                    "target_name": sec.name,
                    "rel_type": rel_type,
                    "source_int": primary.source_int,
                })
            elif primary.type == EntityType.Event:
                rels.append({
                    "source_name": primary.name,
                    "target_name": sec.name,
                    "rel_type": "OCCURRED_AT",
                    "source_int": primary.source_int,
                })

    return rels

_HIGH_RISK_PORTS = {22, 23, 445, 3389, 8080, 8443}

_GRADE_CONFIDENCE = {
    "A": 0.90, "B": 0.75, "C": 0.60,
    "D": 0.40, "E": 0.25, "F": 0.10,
}


def _extract_name(normalized: dict[str, Any], entity_type: str) -> str:
    """Extract the best name from normalized data for a given entity type."""
    for field in _NAME_FIELDS.get(entity_type, ["name"]):
        val = normalized.get(field)
        if val and isinstance(val, str) and val.strip():
            return val.strip()[:200]
    # Fallback: first non-empty string value
    for v in normalized.values():
        if isinstance(v, str) and v.strip() and v != entity_type:
            return v.strip()[:200]
    return f"Unknown {entity_type}"


def _compute_risk_score(normalized: dict[str, Any], entity_type: str) -> float:
    """Compute a 0-10 risk score based on entity properties."""
    score = 0.0
    vulns = normalized.get("vulns", [])
    if vulns:
        score += min(len(vulns) * 1.5, 6.0)
    ports = normalized.get("ports", [])
    risky = [p for p in ports if p in _HIGH_RISK_PORTS]
    score += min(len(risky) * 0.5, 2.0)
    if entity_type == "ThreatActor":
        score += 5.0
    elif entity_type == "Malware":
        score += 6.0
    if normalized.get("malicious_score"):
        try:
            score += min(float(normalized["malicious_score"]), 4.0)
        except (ValueError, TypeError):
            pass
    return min(score, 10.0)


def normalized_to_entities(
    normalized: dict[str, Any],
    source_int: str,
    reliability_grade: str = "F",
    collector_name: str = "unknown",
) -> list[EntityCreate]:
    """Convert a CollectionResult.normalized dict into EntityCreate models.

    A single CollectionResult can produce multiple entities (e.g. a Domain
    plus its resolved IP addresses), so this always returns a list.
    """
    entity_type_str = normalized.get("entity_type", "")
    entity_type = NORMALIZED_TYPE_MAP.get(entity_type_str)
    if entity_type is None:
        return []

    base_confidence = _GRADE_CONFIDENCE.get(reliability_grade[:1].upper(), 0.5)
    name = _extract_name(normalized, entity_type_str)
    lat = normalized.get("latitude")
    lon = normalized.get("longitude")

    # Build properties (exclude meta fields, cap large collections)
    skip = {"entity_type", "name", "latitude", "longitude"}
    properties: dict[str, Any] = {"collector": collector_name}
    for k, v in normalized.items():
        if k in skip or v is None:
            continue
        if isinstance(v, (list, dict)) and len(v) > 50:
            continue
        properties[k] = v

    entities: list[EntityCreate] = [
        EntityCreate(
            name=name,
            type=entity_type,
            properties=properties,
            confidence=base_confidence,
            source_int=source_int,
            risk_score=_compute_risk_score(normalized, entity_type_str),
            latitude=float(lat) if lat is not None else None,
            longitude=float(lon) if lon is not None else None,
        )
    ]

    # Secondary entities: IP addresses from DNS results
    for ip in normalized.get("ip_addresses", [])[:20]:
        if isinstance(ip, str) and ip.strip():
            entities.append(EntityCreate(
                name=ip.strip(),
                type=EntityType.IPAddress,
                properties={"source_domain": name, "collector": collector_name},
                confidence=base_confidence,
                source_int=source_int,
            ))

    # Secondary entities: subdomains
    for sub in normalized.get("subdomains", [])[:30]:
        if isinstance(sub, str) and sub.strip():
            entities.append(EntityCreate(
                name=sub.strip(),
                type=EntityType.Domain,
                properties={
                    "parent_domain": normalized.get("parent_domain", name),
                    "collector": collector_name,
                },
                confidence=round(base_confidence * 0.9, 2),
                source_int=source_int,
            ))

    # Secondary entities: hostnames from Shodan
    for hostname in normalized.get("hostnames", [])[:10]:
        if isinstance(hostname, str) and hostname.strip():
            entities.append(EntityCreate(
                name=hostname.strip(),
                type=EntityType.Domain,
                properties={"resolved_from": name, "collector": collector_name},
                confidence=round(base_confidence * 0.8, 2),
                source_int=source_int,
            ))

    return entities


def infer_relationships(
    primary_entity_name: str,
    secondary_entities: list[EntityCreate],
    source_int: str,
) -> list[dict[str, str]]:
    """Infer relationships between a primary entity and its secondaries.

    Returns dicts with source_name, target_name, rel_type, source_int
    (entity IDs are resolved after creation).
    """
    rels: list[dict[str, str]] = []
    for sec in secondary_entities:
        if sec.type == EntityType.IPAddress:
            rels.append({
                "source_name": sec.name,
                "target_name": primary_entity_name,
                "rel_type": "RESOLVES_TO",
                "source_int": source_int,
            })
        elif sec.type == EntityType.Domain:
            if sec.properties.get("parent_domain"):
                rels.append({
                    "source_name": sec.name,
                    "target_name": primary_entity_name,
                    "rel_type": "PART_OF",
                    "source_int": source_int,
                })
            else:
                rels.append({
                    "source_name": primary_entity_name,
                    "target_name": sec.name,
                    "rel_type": "HOSTS",
                    "source_int": source_int,
                })
    return rels
