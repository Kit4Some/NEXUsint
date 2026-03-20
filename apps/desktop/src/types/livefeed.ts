// Live Feed data types for the NEXUS Multi-INT Fusion platform

export interface LiveFlight {
  callsign: string;
  country: string;
  lat: number;
  lng: number;
  alt: number;
  heading: number;
  speed_knots: number;
  registration: string;
  model: string;
  icao24: string;
  squawk: string;
  airline_code: string;
  aircraft_category: 'plane' | 'heli';
  type: string;
  origin_name: string;
  dest_name: string;
  origin_loc: [number, number] | null;
  dest_loc: [number, number] | null;
  trail: number[][];
  holding: boolean;
  nac_p: number;
  alert_category: string;
  alert_operator: string;
  alert_special: string;
  alert_flag: string;
  alert_color: string;
}

export interface MilitaryFlight extends LiveFlight {
  military_type: string;
  force: string;
}

export interface UAV {
  callsign: string;
  lat: number;
  lng: number;
  alt: number;
  heading: number;
  speed_knots: number;
  icao24: string;
  country: string;
  force: string;
  uav_type: string;
  aircraft_model: string;
  wiki: string;
  type: 'uav';
}

export interface NewsArticle {
  title: string;
  link: string;
  published: string;
  source: string;
  risk_score: number;
  coords: [number, number] | null;
  cluster_count: number;
  articles: NewsArticle[];
  machine_assessment: string | null;
}

export interface Earthquake {
  id: string;
  mag: number;
  lat: number;
  lng: number;
  place: string;
  time: number;
  depth: number;
}

export interface FireHotspot {
  lat: number;
  lng: number;
  frp: number;
  brightness: number;
  confidence: string;
  daynight: string;
  acq_date: string;
}

export interface GPSJammingZone {
  lat: number;
  lng: number;
  severity: string;
  ratio: number;
  degraded: number;
  total: number;
}

export interface SpaceWeather {
  kp_index: number;
  kp_text: string;
  events: Record<string, unknown>[];
}

export interface WeatherRadar {
  time: number;
  host: string;
}

export interface StockData {
  symbol: string;
  price: number;
  change_percent: number;
  up: boolean;
}

export interface OilData {
  name: string;
  price: number;
  change_percent: number;
  up: boolean;
}

export interface NewsFeedConfig {
  name: string;
  url: string;
  weight: number;
}

export interface LiveFeedStatus {
  active: boolean;
  source_timestamps: Record<string, string>;
  source_counts: Record<string, number>;
}

export interface Satellite {
  name: string;
  lat: number;
  lng: number;
  alt: number;
  type: string;
  norad_id: number;
  category: string;
  country: string;
}

export interface GDELTEvent {
  lat: number;
  lng: number;
  title: string;
  url: string;
  tone: number;
  source: string;
  date: string;
}

export interface InternetOutage {
  country: string;
  region: string;
  score: number;
  lat: number;
  lng: number;
}

export interface KiwiSDR {
  name: string;
  lat: number;
  lng: number;
  url: string;
  bands: string;
  users: number;
}

export interface Airport {
  name: string;
  iata: string;
  icao: string;
  lat: number;
  lng: number;
  type: string;
  country: string;
}

export interface ReferencePoint {
  name: string;
  lat: number;
  lng: number;
  type: string;
  country?: string;
}
