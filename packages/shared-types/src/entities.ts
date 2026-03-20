export enum EntityType {
  Person = 'Person',
  Organization = 'Organization',
  Location = 'Location',
  Event = 'Event',
  Object = 'Object',
  SocialAccount = 'SocialAccount',
  Post = 'Post',
  Hashtag = 'Hashtag',
  SatelliteImage = 'SatelliteImage',
  GeoFeature = 'GeoFeature',
  GeoFence = 'GeoFence',
  Aircraft = 'Aircraft',
  Vessel = 'Vessel',
  FlightPath = 'FlightPath',
  VoyageTrack = 'VoyageTrack',
  IPAddress = 'IPAddress',
  Domain = 'Domain',
  Certificate = 'Certificate',
  ThreatActor = 'ThreatActor',
  Malware = 'Malware',
  Vulnerability = 'Vulnerability',
  Indicator = 'Indicator',
}

export enum RelationshipType {
  // Social
  OwnsAccount = 'OWNS_ACCOUNT',
  Posted = 'POSTED',
  Mentioned = 'MENTIONED',
  Follows = 'FOLLOWS',
  RepliedTo = 'REPLIED_TO',
  // Geo
  LocatedAt = 'LOCATED_AT',
  ObservedAt = 'OBSERVED_AT',
  DepartedFrom = 'DEPARTED_FROM',
  ArrivedAt = 'ARRIVED_AT',
  WithinGeofence = 'WITHIN_GEOFENCE',
  // Infrastructure
  ResolvesTo = 'RESOLVES_TO',
  Hosts = 'HOSTS',
  RegisteredBy = 'REGISTERED_BY',
  SignedWith = 'SIGNED_WITH',
  CommunicatesWith = 'COMMUNICATES_WITH',
  // Intelligence
  AttributedTo = 'ATTRIBUTED_TO',
  Targets = 'TARGETS',
  Uses = 'USES',
  Indicates = 'INDICATES',
  Exploits = 'EXPLOITS',
  PartOf = 'PART_OF',
  // Fusion
  CorroboratedBy = 'CORROBORATED_BY',
  Contradicts = 'CONTRADICTS',
  DerivedFrom = 'DERIVED_FROM',
  SameAs = 'SAME_AS',
}

export interface Entity {
  id: string;
  type: EntityType;
  name: string;
  properties: Record<string, unknown>;
  confidence: number;
  sourceInt: string;
  riskScore: number;
  location?: { latitude: number; longitude: number } | null;
  embedding?: number[] | null;
  firstSeen: string;
  lastSeen: string;
  createdAt: string;
  updatedAt: string;
}

export interface Relationship {
  id: string;
  type: RelationshipType;
  sourceId: string;
  targetId: string;
  confidence: number;
  sourceInt: string;
  timestamp: string | null;
  method: 'manual' | 'llm' | 'ner' | 'pattern' | 'fusion';
  properties: Record<string, unknown>;
}

export interface EntitySearchParams {
  type?: EntityType;
  query?: string;
  sourceInt?: string;
  minConfidence?: number;
  limit?: number;
  offset?: number;
}

export interface SubGraph {
  nodes: Entity[];
  edges: Relationship[];
}
