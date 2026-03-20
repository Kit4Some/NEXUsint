"""Application-level Prometheus metrics for NEXUS platform."""

from prometheus_client import Counter, Gauge, Histogram

# Entity metrics
entities_total = Gauge(
    "nexus_entities_total",
    "Total number of entities in the knowledge graph",
)

# Investigation metrics
investigations_active = Gauge(
    "nexus_investigations_active",
    "Number of currently active investigations",
)

# Collection job metrics
collection_jobs_total = Counter(
    "nexus_collection_jobs_total",
    "Total collection jobs processed",
    ["int_type", "status"],
)

# Cache metrics
cache_hits_total = Counter(
    "nexus_cache_hits_total",
    "Total cache hits",
    ["domain"],
)

cache_misses_total = Counter(
    "nexus_cache_misses_total",
    "Total cache misses",
    ["domain"],
)

# Neo4j query metrics
neo4j_query_duration = Histogram(
    "nexus_neo4j_query_duration_seconds",
    "Neo4j query duration in seconds",
    ["query_type"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# WebSocket metrics
websocket_connections = Gauge(
    "nexus_websocket_connections",
    "Number of active WebSocket connections",
)

# Analytics metrics
anomalies_detected = Counter(
    "nexus_anomalies_detected_total",
    "Total anomalies detected",
    ["anomaly_type"],
)
