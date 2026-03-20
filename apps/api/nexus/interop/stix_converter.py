"""NEXUS entity <-> STIX 2.1 SDO/SRO conversion engine."""

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

# NEXUS EntityType -> STIX 2.1 SDO type mapping (from stix-mapping.ttl)
NEXUS_TO_STIX_TYPE: dict[str, str] = {
    "ThreatActor": "threat-actor",
    "Malware": "malware",
    "Vulnerability": "vulnerability",
    "IPAddress": "ipv4-addr",
    "Domain": "domain-name",
    "Certificate": "x509-certificate",
    "Person": "identity",
    "Organization": "identity",
    "Location": "location",
    "Event": "observed-data",
    "SocialAccount": "user-account",
    "Hash": "file",
}

# Reverse mapping: STIX type -> primary NEXUS type
STIX_TO_NEXUS_TYPE: dict[str, str] = {
    "threat-actor": "ThreatActor",
    "malware": "Malware",
    "vulnerability": "Vulnerability",
    "ipv4-addr": "IPAddress",
    "ipv6-addr": "IPAddress",
    "domain-name": "Domain",
    "x509-certificate": "Certificate",
    "identity": "Person",
    "location": "Location",
    "observed-data": "Event",
    "user-account": "SocialAccount",
    "file": "Hash",
    "indicator": "Indicator",
    "campaign": "Event",
}

# NEXUS relationship type -> STIX SRO relationship_type
NEXUS_TO_STIX_REL: dict[str, str] = {
    "ATTRIBUTED_TO": "attributed-to",
    "TARGETS": "targets",
    "USES": "uses",
    "INDICATES": "indicates",
    "LOCATED_AT": "located-at",
    "PART_OF": "part-of",
    "COMMUNICATES_WITH": "communicates-with",
    "HOSTS": "hosts",
    "RESOLVES_TO": "resolves-to",
    "AFFILIATED_WITH": "related-to",
    "SAME_AS": "related-to",
    "CORROBORATED_BY": "related-to",
}

# Reverse mapping
STIX_TO_NEXUS_REL: dict[str, str] = {
    "attributed-to": "ATTRIBUTED_TO",
    "targets": "TARGETS",
    "uses": "USES",
    "indicates": "INDICATES",
    "located-at": "LOCATED_AT",
    "part-of": "PART_OF",
    "communicates-with": "COMMUNICATES_WITH",
    "hosts": "HOSTS",
    "resolves-to": "RESOLVES_TO",
    "related-to": "AFFILIATED_WITH",
}

# Deterministic UUID5 namespace for NEXUS -> STIX ID generation
_NEXUS_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


class STIXConverter:
    """Converts between NEXUS entities and STIX 2.1 objects."""

    def entity_to_sdo(self, entity: dict[str, Any]) -> dict[str, Any] | None:
        """Convert a NEXUS entity to a STIX 2.1 SDO."""
        entity_type = entity.get("type", "") or entity.get("entity_type", "")
        stix_type = NEXUS_TO_STIX_TYPE.get(entity_type)

        if not stix_type:
            logger.debug(
                "stix.unsupported_entity_type",
                entity_type=entity_type,
                entity_id=entity.get("id", ""),
            )
            return None

        nexus_id = entity.get("id", "")
        stix_id = self._generate_stix_id(stix_type, nexus_id)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        sdo: dict[str, Any] = {
            "type": stix_type,
            "spec_version": "2.1",
            "id": stix_id,
            "created": entity.get("created_at", now),
            "modified": entity.get("updated_at", now),
        }

        # Map type-specific properties
        name = entity.get("name", "")
        if stix_type == "threat-actor":
            sdo["name"] = name
            sdo["threat_actor_types"] = entity.get("properties", {}).get("types", ["unknown"])
            sdo["confidence"] = int((entity.get("confidence", 0.5)) * 100)

        elif stix_type == "malware":
            sdo["name"] = name
            sdo["is_family"] = entity.get("properties", {}).get("is_family", False)
            sdo["malware_types"] = entity.get("properties", {}).get("types", ["unknown"])

        elif stix_type == "vulnerability":
            sdo["name"] = name
            sdo["description"] = entity.get("properties", {}).get("description", "")
            if "cve" in entity.get("properties", {}):
                sdo["external_references"] = [{
                    "source_name": "cve",
                    "external_id": entity["properties"]["cve"],
                }]

        elif stix_type == "ipv4-addr":
            sdo["value"] = entity.get("properties", {}).get("address", name)

        elif stix_type == "domain-name":
            sdo["value"] = name

        elif stix_type == "x509-certificate":
            props = entity.get("properties", {})
            sdo["subject"] = props.get("subject", "")
            sdo["issuer"] = props.get("issuer", "")
            sdo["serial_number"] = props.get("serial_number", "")

        elif stix_type == "identity":
            sdo["name"] = name
            sdo["identity_class"] = (
                "organization" if entity_type == "Organization" else "individual"
            )

        elif stix_type == "location":
            sdo["name"] = name
            if "latitude" in entity:
                sdo["latitude"] = entity["latitude"]
            if "longitude" in entity:
                sdo["longitude"] = entity["longitude"]
            props = entity.get("properties", {})
            if "country" in props:
                sdo["country"] = props["country"]

        elif stix_type == "observed-data":
            sdo["first_observed"] = entity.get("created_at", now)
            sdo["last_observed"] = entity.get("updated_at", now)
            sdo["number_observed"] = 1

        elif stix_type == "user-account":
            sdo["account_login"] = name
            sdo["display_name"] = entity.get("properties", {}).get("display_name", name)

        else:
            sdo["name"] = name

        # Add NEXUS metadata as custom properties
        sdo["x_nexus_id"] = nexus_id
        sdo["x_nexus_source_int"] = entity.get("sourceInt", entity.get("source_int", ""))
        sdo["x_nexus_confidence"] = entity.get("confidence", 0.0)
        sdo["x_nexus_risk_score"] = entity.get("riskScore", entity.get("risk_score", 0.0))

        return sdo

    def relationship_to_sro(
        self,
        relationship: dict[str, Any],
        source_stix_id: str,
        target_stix_id: str,
    ) -> dict[str, Any] | None:
        """Convert a NEXUS relationship to a STIX 2.1 SRO."""
        rel_type = relationship.get("type", "") or relationship.get("relationship_type", "")
        stix_rel_type = NEXUS_TO_STIX_REL.get(rel_type)

        if not stix_rel_type:
            logger.debug("stix.unsupported_rel_type", rel_type=rel_type)
            return None

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        rel_id = relationship.get("id", f"{rel_type}:{source_stix_id}:{target_stix_id}")

        sro: dict[str, Any] = {
            "type": "relationship",
            "spec_version": "2.1",
            "id": self._generate_stix_id("relationship", rel_id),
            "created": relationship.get("created_at", now),
            "modified": now,
            "relationship_type": stix_rel_type,
            "source_ref": source_stix_id,
            "target_ref": target_stix_id,
            "confidence": int((relationship.get("confidence", 0.5)) * 100),
        }

        return sro

    def sdo_to_entity(self, sdo: dict[str, Any]) -> dict[str, Any]:
        """Convert a STIX 2.1 SDO back to a NEXUS entity dict."""
        stix_type = sdo.get("type", "")
        nexus_type = STIX_TO_NEXUS_TYPE.get(stix_type, "Object")

        entity: dict[str, Any] = {
            "id": sdo.get("x_nexus_id", str(uuid.uuid4())),
            "type": nexus_type,
            "name": sdo.get("name", sdo.get("value", "")),
            "confidence": sdo.get("x_nexus_confidence", sdo.get("confidence", 50) / 100.0),
            "sourceInt": sdo.get("x_nexus_source_int", "STIX_IMPORT"),
            "riskScore": sdo.get("x_nexus_risk_score", 0.0),
            "properties": {},
        }

        # Extract type-specific properties
        if stix_type == "ipv4-addr":
            entity["properties"]["address"] = sdo.get("value", "")
        elif stix_type == "threat-actor":
            entity["properties"]["types"] = sdo.get("threat_actor_types", [])
        elif stix_type == "malware":
            entity["properties"]["types"] = sdo.get("malware_types", [])
            entity["properties"]["is_family"] = sdo.get("is_family", False)
        elif stix_type == "vulnerability":
            entity["properties"]["description"] = sdo.get("description", "")
            refs = sdo.get("external_references", [])
            for ref in refs:
                if ref.get("source_name") == "cve":
                    entity["properties"]["cve"] = ref.get("external_id", "")
        elif stix_type == "identity":
            entity["properties"]["identity_class"] = sdo.get("identity_class", "")
        elif stix_type == "location":
            if "latitude" in sdo:
                entity["latitude"] = sdo["latitude"]
            if "longitude" in sdo:
                entity["longitude"] = sdo["longitude"]
            if "country" in sdo:
                entity["properties"]["country"] = sdo["country"]

        return entity

    def sro_to_relationship(
        self,
        sro: dict[str, Any],
        id_map: dict[str, str],
    ) -> dict[str, Any]:
        """Convert a STIX 2.1 SRO back to a NEXUS relationship dict."""
        stix_rel_type = sro.get("relationship_type", "")
        nexus_rel_type = STIX_TO_NEXUS_REL.get(stix_rel_type, "RELATED_TO")

        source_stix_id = sro.get("source_ref", "")
        target_stix_id = sro.get("target_ref", "")

        return {
            "type": nexus_rel_type,
            "source_id": id_map.get(source_stix_id, source_stix_id),
            "target_id": id_map.get(target_stix_id, target_stix_id),
            "confidence": sro.get("confidence", 50) / 100.0,
            "properties": {
                "stix_id": sro.get("id", ""),
            },
        }

    def _generate_stix_id(self, stix_type: str, nexus_id: str) -> str:
        """Generate deterministic STIX 2.1 ID from NEXUS ID."""
        deterministic_uuid = uuid.uuid5(_NEXUS_NAMESPACE, f"{stix_type}:{nexus_id}")
        return f"{stix_type}--{deterministic_uuid}"
