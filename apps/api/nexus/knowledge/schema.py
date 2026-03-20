"""POLE schema constants — node labels, relationship types, property keys."""

# Core POLE Node Labels
NODE_LABELS = {
    "Person",
    "Object",
    "Location",
    "Event",
    # SOCMINT
    "SocialAccount",
    "Post",
    "Hashtag",
    "Mention",
    # GEOINT
    "SatelliteImage",
    "GeoFeature",
    "GeoFence",
    # SIGINT
    "Aircraft",
    "Vessel",
    "FlightPath",
    "VoyageTrack",
    # CYBINT
    "IPAddress",
    "Domain",
    "Certificate",
    "ThreatActor",
    "Malware",
    "Vulnerability",
    "Indicator",
    # Meta
    "Entity",
    "Investigation",
}

# Relationship Types
RELATIONSHIP_TYPES = {
    # Social
    "OWNS_ACCOUNT",
    "POSTED",
    "MENTIONED",
    "FOLLOWS",
    "REPLIED_TO",
    # Geo
    "LOCATED_AT",
    "OBSERVED_AT",
    "DEPARTED_FROM",
    "ARRIVED_AT",
    "WITHIN_GEOFENCE",
    # Infrastructure
    "RESOLVES_TO",
    "HOSTS",
    "REGISTERED_BY",
    "SIGNED_WITH",
    "COMMUNICATES_WITH",
    # Intelligence
    "ATTRIBUTED_TO",
    "TARGETS",
    "USES",
    "INDICATES",
    "EXPLOITS",
    "PART_OF",
    # Fusion
    "CORROBORATED_BY",
    "CONTRADICTS",
    "DERIVED_FROM",
    "SAME_AS",
}

# Required relationship metadata properties
RELATIONSHIP_METADATA_KEYS = {
    "confidence",
    "source",
    "timestamp",
    "method",
}

# INT source types
INT_TYPES = {"SOCMINT", "GEOINT", "SIGINT", "CYBINT"}
