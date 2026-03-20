// =============================================================================
// NEXUS OSINT — Neo4j n10s Initialization + Ontology Import
// =============================================================================
// Run this after the n10s plugin is loaded and the database is ready.

// Step 1: Create the unique constraint required by n10s
CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS
FOR (r:Resource) REQUIRE r.uri IS UNIQUE;

// Step 2: Initialize n10s graph configuration
CALL n10s.graphconfig.init({
  handleVocabUris: "MAP",
  handleMultival: "ARRAY",
  keepLangTag: false,
  handleRDFTypes: "LABELS"
});

// Step 3: Register namespace prefixes
CALL n10s.nsprefixes.add("nexus", "http://nexus-osint.org/ontology#");
CALL n10s.nsprefixes.add("stix", "http://docs.oasis-open.org/cti/ns/stix#");
CALL n10s.nsprefixes.add("foaf", "http://xmlns.com/foaf/0.1/");
CALL n10s.nsprefixes.add("sh", "http://www.w3.org/ns/shacl#");

// Step 4: Import the NEXUS OWL ontology
// NOTE: In production, use n10s.onto.import.fetch with a URL or file:// path.
// For Docker, mount the ontology directory and use:
// CALL n10s.onto.import.fetch("file:///ontology/nexus-osint.owl", "RDF/XML");
