export interface GeoPoint {
  latitude: number;
  longitude: number;
  altitude?: number;
  accuracy?: number;
}

export interface BBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface MapEntity {
  id: string;
  type: string;
  name: string;
  position: GeoPoint;
  confidence: number;
  sourceInt: string;
  riskScore: number;
  activity?: string;
  activityType?: 'moving' | 'scanning' | 'communicating' | 'idle' | 'alert';
}

export interface TrackPoint {
  position: GeoPoint;
  timestamp: string;
  speed?: number;
  heading?: number;
  metadata?: Record<string, unknown>;
  activity?: string;
  activityType?: 'moving' | 'scanning' | 'communicating' | 'idle' | 'alert';
  entityType?: string;
  entityName?: string;
  trigger?: string;
}

export interface Track {
  entityId: string;
  entityType: string;
  entityName: string;
  points: TrackPoint[];
}

export interface HeatmapPoint {
  position: GeoPoint;
  weight: number;
}

export interface Cluster {
  id: string;
  position: GeoPoint;
  count: number;
  entityTypes: Record<string, number>;
  radius: number;
}

export interface MapViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  bearing: number;
  pitch: number;
}

export interface FlightData {
  icao24: string;
  callsign: string;
  originCountry: string;
  position: GeoPoint;
  velocity: number;
  heading: number;
  verticalRate: number;
  onGround: boolean;
  lastContact: string;
}

export interface VesselData {
  mmsi: string;
  name: string;
  shipType: string;
  position: GeoPoint;
  speed: number;
  heading: number;
  destination: string;
  draught: number;
  lastUpdate: string;
}
