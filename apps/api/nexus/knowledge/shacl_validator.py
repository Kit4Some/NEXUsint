"""SHACL validation of Neo4j graph data against the NEXUS ontology."""

from dataclasses import dataclass, field
from typing import Any

import structlog

from nexus.knowledge.neo4j_client import Neo4jClient

logger = structlog.get_logger()


@dataclass
class ValidationResult:
    """Result of SHACL-style validation against the ontology."""

    conforms: bool
    violations: list[dict[str, Any]] = field(default_factory=list)
    violation_count: int = 0
    entity_count_checked: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "conforms": self.conforms,
            "violations": self.violations,
            "violation_count": self.violation_count,
            "entity_count_checked": self.entity_count_checked,
        }


# Property constraints derived from NEXUS SHACL shapes
PROPERTY_CONSTRAINTS: dict[str, list[dict[str, Any]]] = {
    "Entity": [
        {
            "path": "confidence",
            "datatype": "float",
            "min_inclusive": 0.0,
            "max_inclusive": 1.0,
            "severity": "warning",
        },
        {
            "path": "sourceInt",
            "datatype": "string",
            "min_count": 1,
            "severity": "violation",
        },
    ],
    "Location": [
        {
            "path": "latitude",
            "datatype": "float",
            "min_inclusive": -90.0,
            "max_inclusive": 90.0,
            "severity": "violation",
        },
        {
            "path": "longitude",
            "datatype": "float",
            "min_inclusive": -180.0,
            "max_inclusive": 180.0,
            "severity": "violation",
        },
    ],
    "IPAddress": [
        {
            "path": "address",
            "datatype": "string",
            "min_count": 1,
            "severity": "violation",
        },
    ],
    "Person": [
        {
            "path": "name",
            "datatype": "string",
            "min_count": 1,
            "severity": "warning",
        },
    ],
}

# Valid relationship domain → range constraints
RELATIONSHIP_CONSTRAINTS: dict[str, dict[str, list[str]]] = {
    "RESOLVES_TO": {"domain": ["Domain"], "range": ["IPAddress"]},
    "LOCATED_AT": {"domain": ["Entity"], "range": ["Location"]},
    "ATTRIBUTED_TO": {"domain": ["Entity"], "range": ["ThreatActor", "Person", "Organization"]},
    "TARGETS": {"domain": ["ThreatActor", "Malware"], "range": ["Entity"]},
    "USES": {"domain": ["ThreatActor"], "range": ["Malware", "Vulnerability"]},
}


class SHACLValidator:
    """Validates Neo4j graph data against SHACL shapes derived from the ontology."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    async def validate_entity(self, entity_id: str) -> ValidationResult:
        """Validate a single entity against its ontology class shape."""
        records = await self._client.execute_read(
            "MATCH (e {id: $id}) RETURN e {.*, __labels: labels(e)} AS entity",
            {"id": entity_id},
        )

        if not records:
            return ValidationResult(
                conforms=False,
                violations=[{
                    "entity_id": entity_id,
                    "path": "",
                    "message": "Entity not found",
                    "severity": "error",
                }],
                violation_count=1,
                entity_count_checked=0,
            )

        entity = records[0]["entity"]
        violations = self._check_entity_constraints(entity_id, entity)

        return ValidationResult(
            conforms=len(violations) == 0,
            violations=violations,
            violation_count=len(violations),
            entity_count_checked=1,
        )

    async def validate_all(
        self,
        entity_type: str | None = None,
        limit: int = 1000,
    ) -> ValidationResult:
        """Validate all entities (or those of a specific type)."""
        if entity_type:
            query = f"""
            MATCH (e:{entity_type})
            RETURN e {{.*, __labels: labels(e)}} AS entity, e.id AS entity_id
            LIMIT $limit
            """
        else:
            query = """
            MATCH (e)
            WHERE e.id IS NOT NULL
            RETURN e {.*, __labels: labels(e)} AS entity, e.id AS entity_id
            LIMIT $limit
            """

        records = await self._client.execute_read(query, {"limit": limit})
        all_violations: list[dict[str, Any]] = []

        for record in records:
            entity = record["entity"]
            entity_id = record["entity_id"]
            violations = self._check_entity_constraints(entity_id, entity)
            all_violations.extend(violations)

        return ValidationResult(
            conforms=len(all_violations) == 0,
            violations=all_violations,
            violation_count=len(all_violations),
            entity_count_checked=len(records),
        )

    async def validate_relationships(self) -> ValidationResult:
        """Validate relationship domain/range constraints from the ontology."""
        violations: list[dict[str, Any]] = []
        checked = 0

        for rel_type, constraints in RELATIONSHIP_CONSTRAINTS.items():
            domain_labels = constraints["domain"]
            range_labels = constraints["range"]

            records = await self._client.execute_read(
                f"""
                MATCH (a)-[r:{rel_type}]->(b)
                RETURN a.id AS source_id, labels(a) AS source_labels,
                       b.id AS target_id, labels(b) AS target_labels,
                       type(r) AS rel_type
                LIMIT 500
                """
            )

            for record in records:
                checked += 1
                source_labels = set(record.get("source_labels", []))
                target_labels = set(record.get("target_labels", []))

                # Check domain: "Entity" matches everything
                if "Entity" not in domain_labels:
                    if not source_labels.intersection(domain_labels):
                        violations.append({
                            "entity_id": record["source_id"],
                            "path": rel_type,
                            "message": (
                                f"Domain violation: {rel_type} source has labels "
                                f"{list(source_labels)}, expected one of {domain_labels}"
                            ),
                            "severity": "warning",
                        })

                # Check range: "Entity" matches everything
                if "Entity" not in range_labels:
                    if not target_labels.intersection(range_labels):
                        violations.append({
                            "entity_id": record["target_id"],
                            "path": rel_type,
                            "message": (
                                f"Range violation: {rel_type} target has labels "
                                f"{list(target_labels)}, expected one of {range_labels}"
                            ),
                            "severity": "warning",
                        })

        return ValidationResult(
            conforms=len(violations) == 0,
            violations=violations,
            violation_count=len(violations),
            entity_count_checked=checked,
        )

    def _check_entity_constraints(
        self,
        entity_id: str,
        entity: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Check entity properties against SHACL-derived constraints."""
        violations: list[dict[str, Any]] = []
        labels = set(entity.get("__labels", []))

        # Always check Entity-level constraints
        types_to_check = ["Entity"]
        for label in labels:
            if label in PROPERTY_CONSTRAINTS:
                types_to_check.append(label)

        for type_name in types_to_check:
            constraints = PROPERTY_CONSTRAINTS.get(type_name, [])
            for constraint in constraints:
                path = constraint["path"]
                value = entity.get(path)

                # Min count check
                min_count = constraint.get("min_count", 0)
                if min_count > 0 and (value is None or value == ""):
                    violations.append({
                        "entity_id": entity_id,
                        "path": path,
                        "message": f"Required property '{path}' is missing (shape: {type_name})",
                        "severity": constraint.get("severity", "violation"),
                    })
                    continue

                if value is None:
                    continue

                # Range checks
                min_val = constraint.get("min_inclusive")
                max_val = constraint.get("max_inclusive")

                if min_val is not None:
                    try:
                        if float(value) < min_val:
                            violations.append({
                                "entity_id": entity_id,
                                "path": path,
                                "message": (
                                    f"Value {value} is below minimum {min_val} "
                                    f"(shape: {type_name})"
                                ),
                                "severity": constraint.get("severity", "warning"),
                            })
                    except (TypeError, ValueError):
                        pass

                if max_val is not None:
                    try:
                        if float(value) > max_val:
                            violations.append({
                                "entity_id": entity_id,
                                "path": path,
                                "message": (
                                    f"Value {value} exceeds maximum {max_val} "
                                    f"(shape: {type_name})"
                                ),
                                "severity": constraint.get("severity", "warning"),
                            })
                    except (TypeError, ValueError):
                        pass

        return violations
