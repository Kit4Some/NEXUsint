"""Neo4j n10s (neosemantics) bridge for OWL ontology operations."""

from pathlib import Path
from typing import Any

import structlog

from nexus.knowledge.neo4j_client import Neo4jClient

logger = structlog.get_logger()

# Default path to the OWL ontology file
_ONTOLOGY_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "ontology"


class OntologyBridge:
    """Manages OWL ontology in Neo4j via the n10s plugin."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    async def initialize_n10s(self) -> None:
        """Initialize n10s configuration — must be called before any import."""
        # Create unique constraint required by n10s
        await self._client.execute_write(
            "CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS "
            "FOR (r:Resource) REQUIRE r.uri IS UNIQUE"
        )

        # Initialize graph config
        await self._client.execute_write(
            """CALL n10s.graphconfig.init({
                handleVocabUris: "MAP",
                handleMultival: "ARRAY",
                keepLangTag: false,
                handleRDFTypes: "LABELS"
            })"""
        )

        # Add namespace prefixes
        prefixes = [
            ("nexus", "http://nexus-osint.org/ontology#"),
            ("stix", "http://docs.oasis-open.org/cti/ns/stix#"),
            ("foaf", "http://xmlns.com/foaf/0.1/"),
            ("sh", "http://www.w3.org/ns/shacl#"),
        ]
        for prefix, uri in prefixes:
            try:
                await self._client.execute_write(
                    "CALL n10s.nsprefixes.add($prefix, $uri)",
                    {"prefix": prefix, "uri": uri},
                )
            except Exception as e:
                logger.debug("ontology.prefix_exists", prefix=prefix, error=str(e))

        logger.info("ontology.n10s_initialized")

    async def import_ontology(
        self,
        owl_url: str | None = None,
        owl_content: str | None = None,
    ) -> dict[str, Any]:
        """Import OWL ontology into Neo4j using n10s."""
        if owl_content:
            records = await self._client.execute_write(
                "CALL n10s.onto.import.inline($content, 'RDF/XML')",
                {"content": owl_content},
            )
        elif owl_url:
            records = await self._client.execute_write(
                "CALL n10s.onto.import.fetch($url, 'RDF/XML')",
                {"url": owl_url},
            )
        else:
            # Load from the default ontology file
            owl_path = _ONTOLOGY_DIR / "nexus-osint.owl"
            if not owl_path.exists():
                raise FileNotFoundError(f"Ontology file not found: {owl_path}")
            content = owl_path.read_text(encoding="utf-8")
            records = await self._client.execute_write(
                "CALL n10s.onto.import.inline($content, 'RDF/XML')",
                {"content": content},
            )

        result = records[0] if records else {}
        logger.info(
            "ontology.imported",
            triples=result.get("triplesLoaded", 0),
            namespaces=result.get("namespaces", 0),
        )
        return result

    async def import_rdf(
        self,
        rdf_content: str,
        format: str = "Turtle",
    ) -> dict[str, Any]:
        """Import RDF triples into Neo4j graph."""
        records = await self._client.execute_write(
            "CALL n10s.rdf.import.inline($rdf, $format)",
            {"rdf": rdf_content, "format": format},
        )
        result = records[0] if records else {}
        logger.info("ontology.rdf_imported", triples=result.get("triplesLoaded", 0))
        return result

    async def export_subgraph_rdf(
        self,
        cypher_query: str,
        params: dict[str, Any] | None = None,
        format: str = "Turtle",
    ) -> str:
        """Export a Cypher-selected subgraph as RDF."""
        records = await self._client.execute_read(
            "CALL n10s.rdf.export.cypher($query, $params)",
            {"query": cypher_query, "params": params or {}},
        )
        # n10s returns serialized RDF as a single string
        if records:
            return records[0].get("rdf", "")
        return ""

    async def export_entity_rdf(
        self,
        entity_id: str,
        depth: int = 1,
    ) -> str:
        """Export an entity and its neighborhood as RDF/Turtle."""
        cypher = """
        MATCH path = (e {id: $entityId})-[*0..$depth]-(n)
        RETURN path
        """
        return await self.export_subgraph_rdf(
            cypher,
            params={"entityId": entity_id, "depth": depth},
        )

    async def get_ontology_classes(self) -> list[dict[str, Any]]:
        """Get all ontology classes from the n10s namespace nodes."""
        records = await self._client.execute_read(
            """
            MATCH (c:Class)
            RETURN c.uri AS uri,
                   c.label AS label,
                   c.comment AS comment,
                   [(c)<-[:SCO]-(sub) | sub.uri] AS subclasses,
                   [(c)-[:SCO]->(parent) | parent.uri] AS superclasses
            ORDER BY c.label
            """
        )
        return records

    async def get_ontology_properties(self) -> list[dict[str, Any]]:
        """Get all ontology properties (object and datatype)."""
        records = await self._client.execute_read(
            """
            MATCH (p:Property)
            RETURN p.uri AS uri,
                   p.label AS label,
                   labels(p) AS types,
                   [(p)-[:DOMAIN]->(d) | d.uri] AS domain,
                   [(p)-[:RANGE]->(r) | r.uri] AS range
            ORDER BY p.label
            """
        )
        return records

    async def ontology_aware_search(
        self,
        class_uri: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query entities using ontology class hierarchy (incl. subclasses).

        This finds all entities whose Neo4j label matches the class or any of
        its subclasses defined in the ontology.
        """
        # First, resolve the class name from URI
        class_name = class_uri.split("#")[-1] if "#" in class_uri else class_uri

        # Find all subclasses
        subclass_records = await self._client.execute_read(
            """
            MATCH (sub)-[:SCO*0..]->(parent:Class)
            WHERE parent.uri ENDS WITH $className
            RETURN COLLECT(DISTINCT
                CASE WHEN sub.uri IS NOT NULL
                     THEN split(sub.uri, '#')[1]
                     ELSE $className END
            ) AS labels
            """,
            {"className": class_name},
        )

        labels = [class_name]
        if subclass_records and subclass_records[0].get("labels"):
            labels = subclass_records[0]["labels"]

        # Build dynamic label match
        label_conditions = " OR ".join(f"e:{label}" for label in labels)

        where_clauses = []
        params: dict[str, Any] = {}
        if filters:
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"filter_{i}"
                where_clauses.append(f"e.{key} = ${param_name}")
                params[param_name] = value

        where_str = ""
        if where_clauses:
            where_str = "WHERE " + " AND ".join(where_clauses)

        query = f"""
        MATCH (e)
        WHERE ({label_conditions})
        {where_str}
        RETURN e {{ .* }} AS entity
        LIMIT 100
        """

        return await self._client.execute_read(query, params)
