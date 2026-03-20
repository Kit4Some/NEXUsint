// =============================================================================
// NEXUS OSINT Platform — Neo4j POLE Schema Initialization
// =============================================================================

// --- UNIQUE CONSTRAINTS ---
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT ip_address IF NOT EXISTS FOR (ip:IPAddress) REQUIRE ip.address IS UNIQUE;
CREATE CONSTRAINT domain_name IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT cert_sha256 IF NOT EXISTS FOR (c:Certificate) REQUIRE c.sha256 IS UNIQUE;
CREATE CONSTRAINT vessel_mmsi IF NOT EXISTS FOR (v:Vessel) REQUIRE v.mmsi IS UNIQUE;
CREATE CONSTRAINT aircraft_icao24 IF NOT EXISTS FOR (a:Aircraft) REQUIRE a.icao24 IS UNIQUE;
CREATE CONSTRAINT vuln_cve IF NOT EXISTS FOR (v:Vulnerability) REQUIRE v.cveId IS UNIQUE;
CREATE CONSTRAINT social_account_handle IF NOT EXISTS FOR (s:SocialAccount) REQUIRE s.platformHandle IS UNIQUE;
CREATE CONSTRAINT investigation_id IF NOT EXISTS FOR (i:Investigation) REQUIRE i.id IS UNIQUE;

// --- FULLTEXT INDEXES ---
CREATE FULLTEXT INDEX person_fulltext IF NOT EXISTS
  FOR (p:Person) ON EACH [p.name, p.aliases];

CREATE FULLTEXT INDEX domain_fulltext IF NOT EXISTS
  FOR (d:Domain) ON EACH [d.name];

CREATE FULLTEXT INDEX threat_actor_fulltext IF NOT EXISTS
  FOR (t:ThreatActor) ON EACH [t.name, t.aliases];

CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
  FOR (e:Entity) ON EACH [e.name];

// --- RANGE INDEXES ---
CREATE INDEX event_timestamp IF NOT EXISTS FOR (e:Event) ON (e.timestamp);
CREATE INDEX post_timestamp IF NOT EXISTS FOR (p:Post) ON (p.timestamp);
CREATE INDEX alert_timestamp IF NOT EXISTS FOR (a:Alert) ON (a.timestamp);
CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX entity_source_int IF NOT EXISTS FOR (e:Entity) ON (e.sourceInt);
CREATE INDEX entity_confidence IF NOT EXISTS FOR (e:Entity) ON (e.confidence);
CREATE INDEX entity_risk_score IF NOT EXISTS FOR (e:Entity) ON (e.riskScore);

// --- LIVE FEED INDEXES ---
CREATE INDEX event_type IF NOT EXISTS FOR (e:Event) ON (e.eventType);
CREATE INDEX aircraft_flight_type IF NOT EXISTS FOR (a:Aircraft) ON (a.flight_type);

// --- FULLTEXT INDEX for Events ---
CREATE FULLTEXT INDEX event_search IF NOT EXISTS
  FOR (e:Event) ON EACH [e.name, e.place];

// --- POINT INDEX (spatial) ---
CREATE POINT INDEX location_coordinates IF NOT EXISTS FOR (l:Location) ON (l.coordinates);

// --- VECTOR INDEX (semantic search, 1536-dim cosine) ---
CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
  FOR (e:Entity) ON (e.embedding)
  OPTIONS {indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }};

// --- REFERENCE NODES (Enums) ---

// INT Types
MERGE (it:ReferenceData:IntType {name: 'SOCMINT', description: 'Social Media Intelligence'});
MERGE (it:ReferenceData:IntType {name: 'GEOINT', description: 'Geospatial Intelligence'});
MERGE (it:ReferenceData:IntType {name: 'SIGINT', description: 'Signals Intelligence (adjacent)'});
MERGE (it:ReferenceData:IntType {name: 'CYBINT', description: 'Cyber Intelligence / Digital Network Intelligence'});

// Risk Levels
MERGE (rl:ReferenceData:RiskLevel {name: 'LOW', value: 1});
MERGE (rl:ReferenceData:RiskLevel {name: 'MEDIUM', value: 2});
MERGE (rl:ReferenceData:RiskLevel {name: 'HIGH', value: 3});
MERGE (rl:ReferenceData:RiskLevel {name: 'CRITICAL', value: 4});

// Admiralty Reliability (Source)
MERGE (ar:ReferenceData:AdmiraltyReliability {grade: 'A', description: 'Completely reliable'});
MERGE (ar:ReferenceData:AdmiraltyReliability {grade: 'B', description: 'Usually reliable'});
MERGE (ar:ReferenceData:AdmiraltyReliability {grade: 'C', description: 'Fairly reliable'});
MERGE (ar:ReferenceData:AdmiraltyReliability {grade: 'D', description: 'Not usually reliable'});
MERGE (ar:ReferenceData:AdmiraltyReliability {grade: 'E', description: 'Unreliable'});
MERGE (ar:ReferenceData:AdmiraltyReliability {grade: 'F', description: 'Reliability cannot be judged'});

// Admiralty Credibility (Information)
MERGE (ac:ReferenceData:AdmiraltyCredibility {grade: '1', description: 'Confirmed by other sources'});
MERGE (ac:ReferenceData:AdmiraltyCredibility {grade: '2', description: 'Probably true'});
MERGE (ac:ReferenceData:AdmiraltyCredibility {grade: '3', description: 'Possibly true'});
MERGE (ac:ReferenceData:AdmiraltyCredibility {grade: '4', description: 'Doubtful'});
MERGE (ac:ReferenceData:AdmiraltyCredibility {grade: '5', description: 'Improbable'});
MERGE (ac:ReferenceData:AdmiraltyCredibility {grade: '6', description: 'Truth cannot be judged'});

// =============================================================================
// SAMPLE DATA — 10 Nodes + 15 Relationships
// =============================================================================

// --- Persons ---
CREATE (p1:Entity:Person {
  id: 'person-001',
  name: 'Alexei Volkov',
  aliases: 'Ghost_Bear, a.volkov',
  nationality: 'RU',
  type: 'Person',
  sourceInt: 'SOCMINT',
  confidence: 0.85,
  riskScore: 7,
  firstSeen: datetime('2024-06-15T10:00:00Z'),
  lastSeen: datetime('2025-02-28T14:30:00Z'),
  createdAt: datetime()
});

CREATE (p2:Entity:Person {
  id: 'person-002',
  name: 'Sarah Chen',
  aliases: 'schen_sec',
  nationality: 'US',
  type: 'Person',
  sourceInt: 'CYBINT',
  confidence: 0.92,
  riskScore: 3,
  firstSeen: datetime('2024-09-01T08:00:00Z'),
  lastSeen: datetime('2025-03-01T12:00:00Z'),
  createdAt: datetime()
});

CREATE (p3:Entity:Person {
  id: 'person-003',
  name: 'Omar Farid',
  aliases: 'darknet_omar',
  nationality: 'EG',
  type: 'Person',
  sourceInt: 'CYBINT',
  confidence: 0.72,
  riskScore: 8,
  firstSeen: datetime('2024-11-10T06:00:00Z'),
  lastSeen: datetime('2025-01-20T22:00:00Z'),
  createdAt: datetime()
});

// --- IP Addresses ---
CREATE (ip1:Entity:IPAddress {
  id: 'ip-001',
  name: '203.0.113.42',
  address: '203.0.113.42',
  asn: 'AS12345',
  country: 'RU',
  type: 'IPAddress',
  sourceInt: 'CYBINT',
  confidence: 0.95,
  riskScore: 9,
  firstSeen: datetime('2024-07-01T00:00:00Z'),
  lastSeen: datetime('2025-03-01T00:00:00Z'),
  createdAt: datetime()
});

CREATE (ip2:Entity:IPAddress {
  id: 'ip-002',
  name: '198.51.100.17',
  address: '198.51.100.17',
  asn: 'AS67890',
  country: 'NL',
  type: 'IPAddress',
  sourceInt: 'CYBINT',
  confidence: 0.88,
  riskScore: 6,
  firstSeen: datetime('2024-08-15T00:00:00Z'),
  lastSeen: datetime('2025-02-20T00:00:00Z'),
  createdAt: datetime()
});

// --- Domains ---
CREATE (d1:Entity:Domain {
  id: 'domain-001',
  name: 'shadow-ops.example.net',
  registrant: 'whoisguard',
  registrationDate: datetime('2024-05-10T00:00:00Z'),
  expiryDate: datetime('2025-05-10T00:00:00Z'),
  type: 'Domain',
  sourceInt: 'CYBINT',
  confidence: 0.91,
  riskScore: 8,
  firstSeen: datetime('2024-05-10T00:00:00Z'),
  lastSeen: datetime('2025-03-01T00:00:00Z'),
  createdAt: datetime()
});

CREATE (d2:Entity:Domain {
  id: 'domain-002',
  name: 'legit-news.example.com',
  registrant: 'Omar Farid',
  registrationDate: datetime('2024-10-01T00:00:00Z'),
  expiryDate: datetime('2025-10-01T00:00:00Z'),
  type: 'Domain',
  sourceInt: 'CYBINT',
  confidence: 0.83,
  riskScore: 5,
  firstSeen: datetime('2024-10-01T00:00:00Z'),
  lastSeen: datetime('2025-02-15T00:00:00Z'),
  createdAt: datetime()
});

// --- ThreatActor ---
CREATE (ta1:Entity:ThreatActor {
  id: 'threat-actor-001',
  name: 'APT-PHANTOM',
  aliases: 'Phantom Group, TEMP.Phantom',
  motivation: 'espionage',
  sophisticationLevel: 'advanced',
  type: 'ThreatActor',
  sourceInt: 'CYBINT',
  confidence: 0.78,
  riskScore: 10,
  firstSeen: datetime('2023-01-01T00:00:00Z'),
  lastSeen: datetime('2025-02-28T00:00:00Z'),
  createdAt: datetime()
});

// --- Location ---
CREATE (loc1:Entity:Location {
  id: 'location-001',
  name: 'Moscow, Russia',
  coordinates: point({latitude: 55.7558, longitude: 37.6173}),
  country: 'RU',
  locationType: 'city',
  type: 'Location',
  sourceInt: 'GEOINT',
  confidence: 0.99,
  riskScore: 0,
  firstSeen: datetime('2024-01-01T00:00:00Z'),
  lastSeen: datetime('2025-03-01T00:00:00Z'),
  createdAt: datetime()
});

// --- Event ---
CREATE (ev1:Entity:Event {
  id: 'event-001',
  name: 'Spear Phishing Campaign Detected',
  eventType: 'ATTACK',
  severity: 'HIGH',
  timestamp: datetime('2025-01-15T14:30:00Z'),
  type: 'Event',
  sourceInt: 'CYBINT',
  confidence: 0.88,
  riskScore: 8,
  firstSeen: datetime('2025-01-15T14:30:00Z'),
  lastSeen: datetime('2025-01-15T14:30:00Z'),
  createdAt: datetime()
});

// =============================================================================
// RELATIONSHIPS (15 total)
// =============================================================================

// 1. Domain resolves to IP
MATCH (d:Domain {name: 'shadow-ops.example.net'}), (ip:IPAddress {address: '203.0.113.42'})
CREATE (d)-[:RESOLVES_TO {
  confidence: 0.95, source: 'CYBINT/PassiveDNS', timestamp: datetime('2024-07-01T00:00:00Z'), method: 'pattern'
}]->(ip);

// 2. IP hosts domain
MATCH (ip:IPAddress {address: '203.0.113.42'}), (d:Domain {name: 'shadow-ops.example.net'})
CREATE (ip)-[:HOSTS {
  confidence: 0.95, source: 'CYBINT/Shodan', timestamp: datetime('2024-07-01T00:00:00Z'), method: 'pattern'
}]->(d);

// 3. ThreatActor attributed to person
MATCH (ta:ThreatActor {name: 'APT-PHANTOM'}), (p:Person {name: 'Alexei Volkov'})
CREATE (ta)-[:ATTRIBUTED_TO {
  confidence: 0.65, source: 'CYBINT/ThreatIntel', timestamp: datetime('2024-12-01T00:00:00Z'), method: 'llm'
}]->(p);

// 4. Person located at location
MATCH (p:Person {name: 'Alexei Volkov'}), (l:Location {name: 'Moscow, Russia'})
CREATE (p)-[:LOCATED_AT {
  confidence: 0.72, source: 'SOCMINT/GeoTag', timestamp: datetime('2025-01-10T08:00:00Z'), method: 'ner'
}]->(l);

// 5. ThreatActor targets person
MATCH (ta:ThreatActor {name: 'APT-PHANTOM'}), (p:Person {name: 'Sarah Chen'})
CREATE (ta)-[:TARGETS {
  confidence: 0.80, source: 'CYBINT/Analysis', timestamp: datetime('2025-01-15T00:00:00Z'), method: 'llm'
}]->(p);

// 6. ThreatActor uses IP
MATCH (ta:ThreatActor {name: 'APT-PHANTOM'}), (ip:IPAddress {address: '203.0.113.42'})
CREATE (ta)-[:USES {
  confidence: 0.88, source: 'CYBINT/Shodan', timestamp: datetime('2024-08-01T00:00:00Z'), method: 'pattern'
}]->(ip);

// 7. Domain registered by person
MATCH (d:Domain {name: 'legit-news.example.com'}), (p:Person {name: 'Omar Farid'})
CREATE (d)-[:REGISTERED_BY {
  confidence: 0.83, source: 'CYBINT/WHOIS', timestamp: datetime('2024-10-01T00:00:00Z'), method: 'pattern'
}]->(p);

// 8. Domain resolves to IP
MATCH (d:Domain {name: 'legit-news.example.com'}), (ip:IPAddress {address: '198.51.100.17'})
CREATE (d)-[:RESOLVES_TO {
  confidence: 0.90, source: 'CYBINT/DNS', timestamp: datetime('2024-10-05T00:00:00Z'), method: 'pattern'
}]->(ip);

// 9. IP communicates with IP
MATCH (ip1:IPAddress {address: '203.0.113.42'}), (ip2:IPAddress {address: '198.51.100.17'})
CREATE (ip1)-[:COMMUNICATES_WITH {
  confidence: 0.75, source: 'CYBINT/NetFlow', timestamp: datetime('2025-01-20T03:00:00Z'), method: 'pattern'
}]->(ip2);

// 10. Person part of ThreatActor
MATCH (p:Person {name: 'Omar Farid'}), (ta:ThreatActor {name: 'APT-PHANTOM'})
CREATE (p)-[:PART_OF {
  confidence: 0.60, source: 'CYBINT/Analysis', timestamp: datetime('2025-01-25T00:00:00Z'), method: 'llm'
}]->(ta);

// 11. Event attributed to ThreatActor
MATCH (ev:Event {name: 'Spear Phishing Campaign Detected'}), (ta:ThreatActor {name: 'APT-PHANTOM'})
CREATE (ev)-[:ATTRIBUTED_TO {
  confidence: 0.82, source: 'CYBINT/ThreatIntel', timestamp: datetime('2025-01-15T14:30:00Z'), method: 'llm'
}]->(ta);

// 12. Event targets person
MATCH (ev:Event {name: 'Spear Phishing Campaign Detected'}), (p:Person {name: 'Sarah Chen'})
CREATE (ev)-[:TARGETS {
  confidence: 0.88, source: 'CYBINT/EmailAnalysis', timestamp: datetime('2025-01-15T14:30:00Z'), method: 'pattern'
}]->(p);

// 13. Person uses domain (SOCMINT)
MATCH (p:Person {name: 'Alexei Volkov'}), (d:Domain {name: 'shadow-ops.example.net'})
CREATE (p)-[:USES {
  confidence: 0.70, source: 'SOCMINT/PostAnalysis', timestamp: datetime('2024-09-15T00:00:00Z'), method: 'ner'
}]->(d);

// 14. Corroboration: CYBINT corroborates SOCMINT finding
MATCH (ip:IPAddress {address: '203.0.113.42'}), (p:Person {name: 'Alexei Volkov'})
CREATE (ip)-[:CORROBORATED_BY {
  confidence: 0.72, source: 'FUSION/CrossINT', timestamp: datetime('2025-02-01T00:00:00Z'), method: 'fusion'
}]->(p);

// 15. IP located at location
MATCH (ip:IPAddress {address: '203.0.113.42'}), (l:Location {name: 'Moscow, Russia'})
CREATE (ip)-[:LOCATED_AT {
  confidence: 0.85, source: 'CYBINT/GeoIP', timestamp: datetime('2025-01-01T00:00:00Z'), method: 'pattern'
}]->(l);
