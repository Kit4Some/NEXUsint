"""Knowledge Graph layer — Neo4j POLE schema interactions."""

from nexus.knowledge.ontology_bridge import OntologyBridge
from nexus.knowledge.shacl_validator import SHACLValidator

__all__ = ["OntologyBridge", "SHACLValidator"]
