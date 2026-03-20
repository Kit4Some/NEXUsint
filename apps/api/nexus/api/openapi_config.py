"""OpenAPI metadata configuration for enhanced API documentation."""

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Authentication — JWT login, token refresh, logout, password management",
    },
    {
        "name": "entities",
        "description": "Entity CRUD — search, create, update, merge entities in the knowledge graph",
    },
    {
        "name": "investigations",
        "description": "Investigation lifecycle — create, execute, monitor, and report on intelligence investigations",
    },
    {
        "name": "map",
        "description": "Map queries — bounding box entity search, heatmaps, entity tracks",
    },
    {
        "name": "collect",
        "description": "Intelligence collection — trigger CYBINT, SOCMINT, SIGINT, GEOINT collection jobs",
    },
    {
        "name": "analytics",
        "description": "Graph analytics — community detection, centrality, anomaly detection, temporal analysis",
    },
    {
        "name": "sigint",
        "description": "SIGINT tracking — real-time flight (ADS-B) and vessel (AIS) tracking",
    },
    {
        "name": "socmint",
        "description": "SOCMINT operations — username search across social platforms",
    },
    {
        "name": "fusion",
        "description": "Entity fusion — cross-source correlation, evidence combination, entity resolution",
    },
    {
        "name": "geoint",
        "description": "GEOINT services — satellite imagery search, OSM features, geocoding",
    },
    {
        "name": "ontology",
        "description": "Ontology management — OWL import/export, SHACL validation, RDF operations",
    },
    {
        "name": "stix",
        "description": "STIX 2.1 interoperability — export/import STIX bundles, validation",
    },
    {
        "name": "reports",
        "description": "Report generation — PDF, HTML, JSON, STIX format intelligence reports",
    },
]

OPENAPI_CONFIG = {
    "title": "NEXUS OSINT Platform API",
    "description": (
        "Multi-INT Fusion OSINT Platform — REST API for intelligence collection, "
        "knowledge graph management, investigation orchestration, and report generation.\n\n"
        "## Authentication\n"
        "All endpoints (except `/auth/login` and `/health`) require a Bearer JWT token.\n\n"
        "## Rate Limiting\n"
        "Default: 100 requests/minute per IP. Auth endpoints: 5 requests/minute.\n\n"
        "## WebSocket\n"
        "Real-time updates via Socket.IO at the root path. Requires JWT token in handshake.\n\n"
        "## INT Types\n"
        "- **CYBINT** — Cyber intelligence (Shodan, VirusTotal, DNS, WHOIS)\n"
        "- **SOCMINT** — Social media intelligence (Twitter, Reddit, Telegram)\n"
        "- **SIGINT** — Signals intelligence (ADS-B flights, AIS vessels)\n"
        "- **GEOINT** — Geospatial intelligence (Sentinel-2, OSM, geocoding)\n"
    ),
    "version": "0.2.0",
    "contact": {
        "name": "NEXUS OSINT",
        "url": "https://github.com/nexus-osint/nexus-msint",
    },
    "license_info": {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    "openapi_tags": OPENAPI_TAGS,
}
