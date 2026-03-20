import { ScatterplotLayer, PathLayer } from '@deck.gl/layers';
import type { PickingInfo } from '@deck.gl/core';
import type { LiveFlight, MilitaryFlight, UAV, GPSJammingZone } from '@/types/livefeed';

// --- Color constants ---

const COLOR_CYAN: [number, number, number] = [0, 200, 255];
const COLOR_CYAN_TRAIL: [number, number, number, number] = [0, 200, 255, 100];
const COLOR_RED: [number, number, number] = [255, 60, 60];
const COLOR_ORANGE: [number, number, number] = [255, 160, 40];
const COLOR_YELLOW: [number, number, number] = [255, 220, 40];
const COLOR_AMBER_PULSE: [number, number, number, number] = [255, 180, 40, 140];

const ALERT_COLOR_MAP: Record<string, [number, number, number]> = {
  red: [255, 60, 60],
  orange: [255, 140, 40],
  yellow: [255, 220, 60],
  green: [60, 220, 100],
  blue: [60, 140, 255],
  purple: [180, 80, 255],
};

// --- Commercial flights ---

export function createCommercialFlightLayer(
  flights: LiveFlight[],
  onClick?: (info: PickingInfo) => void,
) {
  return new ScatterplotLayer<LiveFlight>({
    id: 'commercial-flights',
    data: flights,
    getPosition: (d) => [d.lng, d.lat, d.alt],
    getFillColor: COLOR_CYAN,
    getLineColor: [0, 0, 0, 80],
    getRadius: 4,
    radiusMinPixels: 3,
    radiusMaxPixels: 8,
    lineWidthMinPixels: 1,
    stroked: true,
    filled: true,
    pickable: true,
    antialiasing: true,
    onClick: onClick ?? undefined,
    updateTriggers: {
      getPosition: [flights.length],
    },
  });
}

// --- Military flights ---

export function createMilitaryFlightLayer(
  flights: MilitaryFlight[],
  onClick?: (info: PickingInfo) => void,
) {
  return new ScatterplotLayer<MilitaryFlight>({
    id: 'military-flights',
    data: flights,
    getPosition: (d) => [d.lng, d.lat, d.alt],
    getFillColor: COLOR_RED,
    getLineColor: [180, 0, 0, 160],
    getRadius: 5,
    radiusMinPixels: 4,
    radiusMaxPixels: 10,
    lineWidthMinPixels: 1,
    stroked: true,
    filled: true,
    pickable: true,
    antialiasing: true,
    onClick: onClick ?? undefined,
    updateTriggers: {
      getPosition: [flights.length],
    },
  });
}

// --- Tracked / alert flights ---

export function createTrackedFlightLayer(
  flights: LiveFlight[],
  onClick?: (info: PickingInfo) => void,
) {
  return new ScatterplotLayer<LiveFlight>({
    id: 'tracked-flights',
    data: flights,
    getPosition: (d) => [d.lng, d.lat, d.alt],
    getFillColor: (d) => {
      if (d.alert_color && ALERT_COLOR_MAP[d.alert_color]) {
        return ALERT_COLOR_MAP[d.alert_color];
      }
      return COLOR_ORANGE;
    },
    getLineColor: [0, 0, 0, 100],
    getRadius: 6,
    radiusMinPixels: 5,
    radiusMaxPixels: 12,
    lineWidthMinPixels: 1,
    stroked: true,
    filled: true,
    pickable: true,
    antialiasing: true,
    onClick: onClick ?? undefined,
    updateTriggers: {
      getPosition: [flights.length],
      getFillColor: [flights.map((f) => f.alert_color).join(',')],
    },
  });
}

// --- UAV layer ---

export function createUAVLayer(
  uavs: UAV[],
  onClick?: (info: PickingInfo) => void,
) {
  return new ScatterplotLayer<UAV>({
    id: 'uav-flights',
    data: uavs,
    getPosition: (d) => [d.lng, d.lat, d.alt],
    getFillColor: COLOR_YELLOW,
    getLineColor: [180, 160, 0, 120],
    getRadius: 5,
    radiusMinPixels: 4,
    radiusMaxPixels: 9,
    lineWidthMinPixels: 1,
    stroked: true,
    filled: true,
    pickable: true,
    antialiasing: true,
    onClick: onClick ?? undefined,
    updateTriggers: {
      getPosition: [uavs.length],
    },
  });
}

// --- Flight trail paths ---

interface TrailSegment {
  path: [number, number][];
  callsign: string;
  icao24: string;
}

function flightsToTrails(flights: LiveFlight[]): TrailSegment[] {
  return flights
    .filter((f) => f.trail && f.trail.length >= 2)
    .map((f) => ({
      path: f.trail.map((point) => [point[1], point[0]] as [number, number]),
      callsign: f.callsign,
      icao24: f.icao24,
    }));
}

export function createFlightTrailLayer(flights: LiveFlight[]) {
  const trails = flightsToTrails(flights);

  return new PathLayer<TrailSegment>({
    id: 'flight-trails',
    data: trails,
    getPath: (d) => d.path,
    getColor: COLOR_CYAN_TRAIL,
    getWidth: 1.5,
    widthMinPixels: 1,
    widthMaxPixels: 3,
    capRounded: true,
    jointRounded: true,
    pickable: false,
    updateTriggers: {
      getPath: [trails.length],
    },
  });
}

// --- GPS Jamming zones ---

export function createGPSJammingLayer(zones: GPSJammingZone[]) {
  return new ScatterplotLayer<GPSJammingZone>({
    id: 'gps-jamming-zones',
    data: zones,
    getPosition: (d) => [d.lng, d.lat],
    getFillColor: (d) => {
      const alpha = Math.min(Math.round(d.ratio * 200), 200);
      if (d.severity === 'high' || d.ratio > 0.6) {
        return [255, 50, 50, alpha];
      }
      if (d.severity === 'medium' || d.ratio > 0.3) {
        return [255, 140, 40, alpha];
      }
      return [255, 200, 60, alpha];
    },
    getRadius: (d) => {
      const base = 30000;
      return base + d.ratio * 40000;
    },
    radiusMinPixels: 10,
    radiusMaxPixels: 80,
    stroked: true,
    filled: true,
    getLineColor: (d) => {
      if (d.severity === 'high' || d.ratio > 0.6) {
        return [255, 50, 50, 120] as [number, number, number, number];
      }
      return [255, 160, 40, 80] as [number, number, number, number];
    },
    lineWidthMinPixels: 1,
    pickable: true,
    antialiasing: true,
    updateTriggers: {
      getPosition: [zones.length],
      getFillColor: [zones.map((z) => z.ratio).join(',')],
      getRadius: [zones.map((z) => z.ratio).join(',')],
    },
  });
}

// --- Holding pattern indicator ---

export function createHoldingPatternLayer(flights: LiveFlight[]) {
  const holdingFlights = flights.filter((f) => f.holding);

  return new ScatterplotLayer<LiveFlight>({
    id: 'holding-patterns',
    data: holdingFlights,
    getPosition: (d) => [d.lng, d.lat],
    getFillColor: COLOR_AMBER_PULSE,
    getRadius: 18000,
    radiusMinPixels: 12,
    radiusMaxPixels: 40,
    stroked: true,
    filled: true,
    getLineColor: [255, 180, 40, 200] as [number, number, number, number],
    lineWidthMinPixels: 2,
    pickable: false,
    antialiasing: true,
    updateTriggers: {
      getPosition: [holdingFlights.length],
    },
  });
}

