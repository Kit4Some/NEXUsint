"""Seed routes — populate Neo4j with realistic OSINT demo data."""

from datetime import datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from nexus.dependencies import get_neo4j
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.knowledge.repository import EntityRepository
from nexus.models.entity import EntityCreate, EntityType, RelationshipCreate, ExtractionMethod

logger = structlog.get_logger()
router = APIRouter()

# ---------------------------------------------------------------------------
# Demo entity definitions
# ---------------------------------------------------------------------------

_DEMO_ENTITIES: list[dict[str, Any]] = [
    # --- Persons ---
    {"name": "Viktor Petrov", "type": "Person", "source_int": "SOCMINT", "confidence": 0.85, "risk_score": 7.2, "lat": 55.7558, "lon": 37.6173, "props": {"alias": "v_petrov_x", "nationality": "Russian"}},
    {"name": "Li Wei", "type": "Person", "source_int": "CYBINT", "confidence": 0.78, "risk_score": 6.5, "lat": 39.9042, "lon": 116.4074, "props": {"alias": "ghostshell", "role": "Operator"}},
    {"name": "Sarah Mitchell", "type": "Person", "source_int": "SOCMINT", "confidence": 0.92, "risk_score": 2.1, "lat": 38.9072, "lon": -77.0369, "props": {"role": "Analyst", "affiliation": "CISA"}},
    {"name": "Ahmed Al-Rashid", "type": "Person", "source_int": "SIGINT", "confidence": 0.71, "risk_score": 5.8, "lat": 25.2048, "lon": 55.2708, "props": {"alias": "sandstorm_7", "comms": "encrypted"}},
    {"name": "Elena Volkov", "type": "Person", "source_int": "SOCMINT", "confidence": 0.88, "risk_score": 4.3, "lat": 50.4501, "lon": 30.5234, "props": {"alias": "e_volkov", "role": "Recruiter"}},
    {"name": "James Chen", "type": "Person", "source_int": "CYBINT", "confidence": 0.95, "risk_score": 1.5, "lat": 37.7749, "lon": -122.4194, "props": {"role": "Security Researcher", "employer": "CrowdStrike"}},
    {"name": "Fatima Zahra", "type": "Person", "source_int": "SOCMINT", "confidence": 0.67, "risk_score": 3.9, "lat": 33.5731, "lon": -7.5898, "props": {"alias": "fz_ghost", "platform": "Telegram"}},
    {"name": "Dmitri Sokolov", "type": "Person", "source_int": "CYBINT", "confidence": 0.82, "risk_score": 8.1, "lat": 59.9343, "lon": 30.3351, "props": {"alias": "d_sok0l", "role": "Malware Developer"}},

    # --- Organizations ---
    {"name": "ShadowNet Collective", "type": "Organization", "source_int": "CYBINT", "confidence": 0.76, "risk_score": 9.0, "lat": None, "lon": None, "props": {"type": "Hacking Group", "origin": "Eastern Europe"}},
    {"name": "Meridian Logistics Ltd", "type": "Organization", "source_int": "SIGINT", "confidence": 0.83, "risk_score": 5.5, "lat": 1.3521, "lon": 103.8198, "props": {"type": "Shell Company", "registered": "Singapore"}},
    {"name": "CyberVault Security", "type": "Organization", "source_int": "CYBINT", "confidence": 0.94, "risk_score": 1.2, "lat": 51.5074, "lon": -0.1278, "props": {"type": "InfoSec Company", "employees": 450}},
    {"name": "Phantom Holdings AG", "type": "Organization", "source_int": "CYBINT", "confidence": 0.65, "risk_score": 7.8, "lat": 47.3769, "lon": 8.5417, "props": {"type": "Financial", "status": "Under Investigation"}},
    {"name": "Red Crescent Technologies", "type": "Organization", "source_int": "SIGINT", "confidence": 0.59, "risk_score": 6.2, "lat": 35.6762, "lon": 51.4241, "props": {"type": "Technology", "sector": "Telecommunications"}},
    {"name": "CISA Threat Analysis Division", "type": "Organization", "source_int": "SOCMINT", "confidence": 0.97, "risk_score": 0.5, "lat": 38.8951, "lon": -77.0364, "props": {"type": "Government", "country": "US"}},

    # --- IP Addresses ---
    {"name": "185.220.101.34", "type": "IPAddress", "source_int": "CYBINT", "confidence": 0.91, "risk_score": 8.5, "lat": 52.5200, "lon": 13.4050, "props": {"asn": "AS60729", "isp": "Leaseweb DE", "ports": "22,80,443,8080"}},
    {"name": "103.75.201.18", "type": "IPAddress", "source_int": "CYBINT", "confidence": 0.87, "risk_score": 7.9, "lat": 22.3193, "lon": 114.1694, "props": {"asn": "AS138997", "isp": "Eons Data", "ports": "443,8443"}},
    {"name": "45.153.160.2", "type": "IPAddress", "source_int": "CYBINT", "confidence": 0.79, "risk_score": 9.2, "lat": 48.8566, "lon": 2.3522, "props": {"asn": "AS208476", "tags": "C2,TOR-Exit", "ports": "443,9001"}},
    {"name": "198.51.100.42", "type": "IPAddress", "source_int": "CYBINT", "confidence": 0.83, "risk_score": 6.1, "lat": 40.7128, "lon": -74.0060, "props": {"asn": "AS16509", "isp": "Amazon AWS", "ports": "443"}},
    {"name": "91.234.33.87", "type": "IPAddress", "source_int": "CYBINT", "confidence": 0.74, "risk_score": 7.4, "lat": 55.7558, "lon": 37.6173, "props": {"asn": "AS49505", "tags": "Scanner,Brute-Force"}},
    {"name": "172.67.188.13", "type": "IPAddress", "source_int": "CYBINT", "confidence": 0.68, "risk_score": 3.2, "lat": 37.7749, "lon": -122.4194, "props": {"asn": "AS13335", "isp": "Cloudflare", "ports": "80,443"}},
    {"name": "5.188.86.21", "type": "IPAddress", "source_int": "CYBINT", "confidence": 0.85, "risk_score": 8.8, "lat": 59.9343, "lon": 30.3351, "props": {"asn": "AS202425", "tags": "Botnet-C2,Malware-Delivery"}},
    {"name": "203.0.113.55", "type": "IPAddress", "source_int": "CYBINT", "confidence": 0.72, "risk_score": 5.7, "lat": 35.6762, "lon": 51.4241, "props": {"asn": "AS49666", "isp": "TIC", "ports": "22,443,3389"}},

    # --- Domains ---
    {"name": "shadownet-c2.xyz", "type": "Domain", "source_int": "CYBINT", "confidence": 0.88, "risk_score": 9.5, "lat": 52.5200, "lon": 13.4050, "props": {"registrar": "NameCheap", "created": "2024-08-15", "status": "Active C2"}},
    {"name": "meridian-global.trade", "type": "Domain", "source_int": "CYBINT", "confidence": 0.75, "risk_score": 4.8, "lat": 1.3521, "lon": 103.8198, "props": {"registrar": "GoDaddy", "created": "2023-02-10"}},
    {"name": "phantomvault.io", "type": "Domain", "source_int": "CYBINT", "confidence": 0.82, "risk_score": 7.3, "lat": 47.3769, "lon": 8.5417, "props": {"registrar": "Tucows", "created": "2024-01-22", "privacy": True}},
    {"name": "cyber-vault.co.uk", "type": "Domain", "source_int": "CYBINT", "confidence": 0.96, "risk_score": 0.8, "lat": 51.5074, "lon": -0.1278, "props": {"registrar": "Nominet", "verified": True}},
    {"name": "update-service.cloud", "type": "Domain", "source_int": "CYBINT", "confidence": 0.70, "risk_score": 8.1, "lat": 48.8566, "lon": 2.3522, "props": {"registrar": "NameSilo", "tags": "Phishing,Malware-Delivery"}},
    {"name": "redcrescent-tech.ir", "type": "Domain", "source_int": "CYBINT", "confidence": 0.63, "risk_score": 5.4, "lat": 35.6762, "lon": 51.4241, "props": {"registrar": "IRNIC", "created": "2022-11-03"}},

    # --- Threat Actors ---
    {"name": "APT-SHADOW", "type": "ThreatActor", "source_int": "CYBINT", "confidence": 0.80, "risk_score": 9.3, "lat": None, "lon": None, "props": {"aliases": "ShadowBear,PhantomLock", "origin": "Russia", "motivation": "Espionage"}},
    {"name": "DESERT-VIPER", "type": "ThreatActor", "source_int": "CYBINT", "confidence": 0.72, "risk_score": 8.7, "lat": None, "lon": None, "props": {"origin": "Middle East", "motivation": "Cyber Espionage", "ttps": "Spear-phishing,Watering-hole"}},
    {"name": "JADE-DRAGON", "type": "ThreatActor", "source_int": "CYBINT", "confidence": 0.77, "risk_score": 8.9, "lat": None, "lon": None, "props": {"origin": "China", "motivation": "IP Theft", "ttps": "Supply-chain,Zero-day"}},
    {"name": "PHANTOM-LOCK", "type": "ThreatActor", "source_int": "CYBINT", "confidence": 0.68, "risk_score": 7.5, "lat": None, "lon": None, "props": {"origin": "Unknown", "motivation": "Financial", "ttps": "Ransomware,Double-Extortion"}},

    # --- Locations ---
    {"name": "Moscow, Russia", "type": "Location", "source_int": "GEOINT", "confidence": 0.95, "risk_score": 3.0, "lat": 55.7558, "lon": 37.6173, "props": {"country": "RU", "region": "Moscow Oblast"}},
    {"name": "Singapore", "type": "Location", "source_int": "GEOINT", "confidence": 0.95, "risk_score": 1.5, "lat": 1.3521, "lon": 103.8198, "props": {"country": "SG"}},
    {"name": "Tehran, Iran", "type": "Location", "source_int": "GEOINT", "confidence": 0.90, "risk_score": 4.5, "lat": 35.6762, "lon": 51.4241, "props": {"country": "IR", "region": "Tehran Province"}},
    {"name": "Berlin, Germany", "type": "Location", "source_int": "GEOINT", "confidence": 0.95, "risk_score": 1.0, "lat": 52.5200, "lon": 13.4050, "props": {"country": "DE"}},
    {"name": "Dubai, UAE", "type": "Location", "source_int": "GEOINT", "confidence": 0.93, "risk_score": 2.0, "lat": 25.2048, "lon": 55.2708, "props": {"country": "AE"}},
    {"name": "Hong Kong", "type": "Location", "source_int": "GEOINT", "confidence": 0.95, "risk_score": 2.5, "lat": 22.3193, "lon": 114.1694, "props": {"country": "HK"}},

    # --- Aircraft ---
    {"name": "AC-3C4E21 (B737)", "type": "Aircraft", "source_int": "SIGINT", "confidence": 0.91, "risk_score": 3.5, "lat": 41.0082, "lon": 28.9784, "props": {"icao24": "3c4e21", "callsign": "TK1952", "model": "B737-800", "operator": "Turkish Airlines"}},
    {"name": "AC-A1B2C3 (G550)", "type": "Aircraft", "source_int": "SIGINT", "confidence": 0.85, "risk_score": 6.8, "lat": 25.2532, "lon": 55.3657, "props": {"icao24": "a1b2c3", "callsign": "PHNIX1", "model": "G550", "operator": "Private"}},
    {"name": "AC-4CA7F2 (A320)", "type": "Aircraft", "source_int": "SIGINT", "confidence": 0.89, "risk_score": 2.1, "lat": 48.1103, "lon": 11.5545, "props": {"icao24": "4ca7f2", "callsign": "EI382", "model": "A320", "operator": "Aer Lingus"}},
    {"name": "AC-780B40 (CL600)", "type": "Aircraft", "source_int": "SIGINT", "confidence": 0.78, "risk_score": 7.5, "lat": 55.4101, "lon": 37.9024, "props": {"icao24": "780b40", "callsign": "UKNWN", "model": "CL-600", "operator": "Unknown"}},

    # --- Vessels ---
    {"name": "MV OCEANIC SPIRIT", "type": "Vessel", "source_int": "SIGINT", "confidence": 0.87, "risk_score": 4.2, "lat": 1.2655, "lon": 103.8220, "props": {"mmsi": "563012340", "imo": "9876543", "flag": "Singapore", "type": "Cargo"}},
    {"name": "MV BLACK PEARL", "type": "Vessel", "source_int": "SIGINT", "confidence": 0.73, "risk_score": 8.0, "lat": 26.0667, "lon": 56.2500, "props": {"mmsi": "470123456", "flag": "Unknown", "type": "Yacht", "ais_gap": "72h"}},
    {"name": "MV NORTHERN STAR", "type": "Vessel", "source_int": "SIGINT", "confidence": 0.91, "risk_score": 2.5, "lat": 59.3293, "lon": 18.0686, "props": {"mmsi": "265123000", "flag": "Sweden", "type": "RoRo", "route": "Stockholm-Helsinki"}},
    {"name": "MV CASPIAN TRADER", "type": "Vessel", "source_int": "SIGINT", "confidence": 0.66, "risk_score": 6.9, "lat": 40.4093, "lon": 49.8671, "props": {"mmsi": "423456789", "flag": "Azerbaijan", "type": "Tanker", "sanctions_risk": True}},

    # --- Social Accounts ---
    {"name": "@v_petrov_x", "type": "SocialAccount", "source_int": "SOCMINT", "confidence": 0.82, "risk_score": 5.5, "lat": None, "lon": None, "props": {"platform": "Twitter/X", "followers": 1243, "joined": "2021-03"}},
    {"name": "@sandstorm_ops", "type": "SocialAccount", "source_int": "SOCMINT", "confidence": 0.69, "risk_score": 6.8, "lat": None, "lon": None, "props": {"platform": "Telegram", "members": 458, "type": "Channel"}},
    {"name": "@fz_ghost_channel", "type": "SocialAccount", "source_int": "SOCMINT", "confidence": 0.71, "risk_score": 4.1, "lat": None, "lon": None, "props": {"platform": "Telegram", "members": 892, "type": "Channel"}},
    {"name": "@d_sok0l_dev", "type": "SocialAccount", "source_int": "SOCMINT", "confidence": 0.77, "risk_score": 7.0, "lat": None, "lon": None, "props": {"platform": "GitHub", "repos": 23, "joined": "2020-09"}},
]

# Relationship definitions: (source_idx, target_idx, type, confidence, source_int)
_DEMO_RELATIONSHIPS: list[tuple[int, int, str, float, str]] = [
    # Person → Organization affiliations
    (0, 8, "PART_OF", 0.82, "SOCMINT"),          # Petrov → ShadowNet
    (1, 8, "PART_OF", 0.75, "CYBINT"),            # Li Wei → ShadowNet
    (7, 8, "PART_OF", 0.88, "CYBINT"),            # Sokolov → ShadowNet
    (2, 13, "PART_OF", 0.95, "SOCMINT"),          # Mitchell → CISA
    (5, 10, "PART_OF", 0.93, "CYBINT"),           # Chen → CyberVault
    (3, 12, "COMMUNICATES_WITH", 0.65, "SIGINT"), # Al-Rashid → Red Crescent
    (4, 8, "COMMUNICATES_WITH", 0.71, "SOCMINT"), # Volkov → ShadowNet

    # Person → SocialAccount ownership
    (0, 46, "OWNS_ACCOUNT", 0.90, "SOCMINT"),    # Petrov → @v_petrov_x
    (3, 47, "OWNS_ACCOUNT", 0.72, "SOCMINT"),    # Al-Rashid → @sandstorm_ops
    (6, 48, "OWNS_ACCOUNT", 0.78, "SOCMINT"),    # Fatima → @fz_ghost_channel
    (7, 49, "OWNS_ACCOUNT", 0.85, "SOCMINT"),    # Sokolov → @d_sok0l_dev

    # ThreatActor → Organization/Person attribution
    (28, 8, "ATTRIBUTED_TO", 0.80, "CYBINT"),     # APT-SHADOW → ShadowNet
    (28, 0, "ATTRIBUTED_TO", 0.70, "CYBINT"),     # APT-SHADOW → Petrov
    (29, 3, "ATTRIBUTED_TO", 0.62, "CYBINT"),     # DESERT-VIPER → Al-Rashid
    (30, 1, "ATTRIBUTED_TO", 0.68, "CYBINT"),     # JADE-DRAGON → Li Wei
    (31, 11, "ATTRIBUTED_TO", 0.55, "CYBINT"),    # PHANTOM-LOCK → Phantom Holdings

    # IP → Domain resolution
    (14, 22, "RESOLVES_TO", 0.92, "CYBINT"),      # 185.220.101.34 → shadownet-c2.xyz
    (16, 26, "RESOLVES_TO", 0.85, "CYBINT"),      # 45.153.160.2 → update-service.cloud
    (15, 24, "RESOLVES_TO", 0.78, "CYBINT"),      # 103.75.201.18 → phantomvault.io
    (19, 25, "RESOLVES_TO", 0.95, "CYBINT"),      # 172.67.188.13 → cyber-vault.co.uk
    (21, 27, "RESOLVES_TO", 0.70, "CYBINT"),      # 203.0.113.55 → redcrescent-tech.ir

    # Domain → Organization hosting
    (22, 8, "HOSTS", 0.85, "CYBINT"),             # shadownet-c2.xyz → ShadowNet
    (23, 9, "HOSTS", 0.80, "CYBINT"),             # meridian-global.trade → Meridian Logistics
    (24, 11, "HOSTS", 0.75, "CYBINT"),            # phantomvault.io → Phantom Holdings
    (25, 10, "HOSTS", 0.95, "CYBINT"),            # cyber-vault.co.uk → CyberVault
    (27, 12, "HOSTS", 0.65, "CYBINT"),            # redcrescent-tech.ir → Red Crescent

    # ThreatActor → IP/Domain usage
    (28, 14, "USES", 0.82, "CYBINT"),             # APT-SHADOW → 185.220.101.34
    (28, 22, "USES", 0.88, "CYBINT"),             # APT-SHADOW → shadownet-c2.xyz
    (29, 21, "USES", 0.65, "CYBINT"),             # DESERT-VIPER → 203.0.113.55
    (30, 15, "USES", 0.72, "CYBINT"),             # JADE-DRAGON → 103.75.201.18
    (31, 16, "USES", 0.77, "CYBINT"),             # PHANTOM-LOCK → 45.153.160.2
    (31, 26, "USES", 0.80, "CYBINT"),             # PHANTOM-LOCK → update-service.cloud

    # ThreatActor targets
    (28, 10, "TARGETS", 0.73, "CYBINT"),          # APT-SHADOW → CyberVault
    (29, 13, "TARGETS", 0.60, "CYBINT"),          # DESERT-VIPER → CISA
    (30, 10, "TARGETS", 0.65, "CYBINT"),          # JADE-DRAGON → CyberVault
    (31, 9, "TARGETS", 0.70, "CYBINT"),           # PHANTOM-LOCK → Meridian Logistics

    # Person → Location
    (0, 32, "LOCATED_AT", 0.90, "GEOINT"),        # Petrov → Moscow
    (3, 36, "LOCATED_AT", 0.80, "GEOINT"),        # Al-Rashid → Dubai
    (1, 37, "LOCATED_AT", 0.75, "GEOINT"),        # Li Wei → Hong Kong
    (2, 35, "LOCATED_AT", 0.95, "GEOINT"),        # Mitchell → Berlin (conference)
    (7, 32, "LOCATED_AT", 0.82, "GEOINT"),        # Sokolov → Moscow

    # Organization → Location
    (9, 33, "LOCATED_AT", 0.90, "GEOINT"),        # Meridian → Singapore
    (10, 35, "LOCATED_AT", 0.95, "GEOINT"),       # CyberVault → Berlin
    (12, 34, "LOCATED_AT", 0.85, "GEOINT"),       # Red Crescent → Tehran

    # IP → Location
    (14, 35, "LOCATED_AT", 0.88, "GEOINT"),       # 185.220.101.34 → Berlin
    (15, 37, "LOCATED_AT", 0.85, "GEOINT"),       # 103.75.201.18 → Hong Kong

    # Communication links
    (0, 7, "COMMUNICATES_WITH", 0.78, "SIGINT"),  # Petrov ↔ Sokolov
    (0, 4, "COMMUNICATES_WITH", 0.72, "SOCMINT"), # Petrov ↔ Volkov
    (3, 6, "COMMUNICATES_WITH", 0.65, "SOCMINT"), # Al-Rashid ↔ Fatima
    (1, 7, "COMMUNICATES_WITH", 0.70, "CYBINT"),  # Li Wei ↔ Sokolov

    # Vessel/Aircraft → Location
    (42, 33, "DEPARTED_FROM", 0.87, "SIGINT"),    # OCEANIC SPIRIT → Singapore
    (43, 36, "LOCATED_AT", 0.73, "SIGINT"),       # BLACK PEARL → Dubai area
    (45, 34, "DEPARTED_FROM", 0.66, "SIGINT"),    # CASPIAN TRADER → Tehran area

    # Aircraft → Person (linked via travel)
    (39, 3, "CARRIES", 0.60, "SIGINT"),           # G550 private → Al-Rashid (suspected)
    (43, 11, "REGISTERED_BY", 0.55, "SIGINT"),    # BLACK PEARL → Phantom Holdings

    # Cross-INT corroboration
    (5, 28, "INVESTIGATES", 0.90, "SOCMINT"),     # Chen → APT-SHADOW
    (2, 29, "INVESTIGATES", 0.88, "SOCMINT"),     # Mitchell → DESERT-VIPER
]


@router.post("/demo")
async def seed_demo_data(driver=Depends(get_neo4j)) -> dict[str, Any]:
    """Populate Neo4j with realistic OSINT demo data for all views."""
    client = Neo4jClient(driver)
    repo = EntityRepository(client)

    # Check if demo data already exists
    existing = await client.execute_read(
        "MATCH (e:Entity) WHERE e.name = 'Viktor Petrov' RETURN count(e) AS cnt"
    )
    if existing and existing[0]["cnt"] > 0:
        total = await client.execute_read("MATCH (e:Entity) RETURN count(e) AS cnt")
        rels = await client.execute_read("MATCH ()-[r]->() RETURN count(r) AS cnt")
        return {
            "status": "already_seeded",
            "entities": total[0]["cnt"] if total else 0,
            "relationships": rels[0]["cnt"] if rels else 0,
        }

    # Create entities
    created_ids: list[str] = []
    for e in _DEMO_ENTITIES:
        entity = EntityCreate(
            name=e["name"],
            type=EntityType(e["type"]),
            source_int=e["source_int"],
            confidence=e["confidence"],
            risk_score=e["risk_score"],
            latitude=e.get("lat"),
            longitude=e.get("lon"),
            properties=e.get("props", {}),
        )
        try:
            result = await repo.create_entity(entity)
            created_ids.append(result.id)
        except Exception as exc:
            logger.warning("seed.entity_failed", name=e["name"], error=str(exc))
            created_ids.append("")

    # Create relationships
    rel_count = 0
    base_time = datetime.utcnow() - timedelta(days=90)
    for idx, (src_idx, tgt_idx, rel_type, conf, src_int) in enumerate(_DEMO_RELATIONSHIPS):
        src_id = created_ids[src_idx] if src_idx < len(created_ids) else ""
        tgt_id = created_ids[tgt_idx] if tgt_idx < len(created_ids) else ""
        if not src_id or not tgt_id:
            continue
        try:
            rel = RelationshipCreate(
                type=rel_type,
                source_id=src_id,
                target_id=tgt_id,
                confidence=conf,
                source_int=src_int,
                method=ExtractionMethod.Fusion,
                timestamp=base_time + timedelta(days=idx * 1.2, hours=idx * 3),
            )
            await repo.create_relationship(rel)
            rel_count += 1
        except Exception as exc:
            logger.warning("seed.rel_failed", type=rel_type, error=str(exc))

    logger.info("seed.completed", entities=len(created_ids), relationships=rel_count)
    return {
        "status": "seeded",
        "entities": len([eid for eid in created_ids if eid]),
        "relationships": rel_count,
    }
