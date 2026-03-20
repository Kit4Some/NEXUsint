import { ScatterplotLayer } from '@deck.gl/layers';
import type {
  InternetOutage,
  GDELTEvent,
  Airport,
  ReferencePoint,
  KiwiSDR,
} from '@/types/livefeed';

/**
 * Internet outage layer — red circles with radius proportional to outage score.
 */
export function createInternetOutageLayer(outages: InternetOutage[]) {
  if (!outages || outages.length === 0) {
    return new ScatterplotLayer<InternetOutage>({
      id: 'internet-outages',
      data: [],
      getPosition: () => [0, 0],
      visible: false,
    });
  }

  const maxScore = Math.max(...outages.map((o) => o.score), 1);

  return new ScatterplotLayer<InternetOutage>({
    id: 'internet-outages',
    data: outages,
    getPosition: (d) => [d.lng, d.lat],
    getRadius: (d) => {
      const normalized = Math.min(d.score / maxScore, 1);
      return 10000 + normalized * 80000;
    },
    getFillColor: [220, 40, 40, 140],
    radiusMinPixels: 4,
    radiusMaxPixels: 30,
    stroked: true,
    getLineColor: [255, 60, 60, 200],
    getLineWidth: 2,
    lineWidthMinPixels: 1,
    pickable: true,
    updateTriggers: {
      getPosition: [outages.length],
      getRadius: [outages.length],
    },
  });
}

/**
 * GDELT event layer — orange dots for global event data.
 */
export function createGDELTLayer(
  events: GDELTEvent[],
  onClick?: (info: any) => void,
) {
  if (!events || events.length === 0) {
    return new ScatterplotLayer<GDELTEvent>({
      id: 'gdelt-events',
      data: [],
      getPosition: () => [0, 0],
      visible: false,
    });
  }

  return new ScatterplotLayer<GDELTEvent>({
    id: 'gdelt-events',
    data: events,
    getPosition: (d) => [d.lng, d.lat],
    getRadius: 6000,
    getFillColor: (d) => {
      // More negative tone = more red-orange, positive = lighter orange
      const intensity = Math.min(Math.abs(d.tone) / 10, 1);
      return [255, 140 + (1 - intensity) * 60, 50, 180] as [number, number, number, number];
    },
    radiusMinPixels: 3,
    radiusMaxPixels: 12,
    stroked: false,
    pickable: true,
    onClick: onClick
      ? (info) => {
          if (info.object) onClick(info);
        }
      : undefined,
    updateTriggers: {
      getPosition: [events.length],
      getFillColor: [events.length],
    },
  });
}

/**
 * Airport layer — small blue dots.
 */
export function createAirportLayer(airports: Airport[]) {
  if (!airports || airports.length === 0) {
    return new ScatterplotLayer<Airport>({
      id: 'airports',
      data: [],
      getPosition: () => [0, 0],
      visible: false,
    });
  }

  return new ScatterplotLayer<Airport>({
    id: 'airports',
    data: airports,
    getPosition: (d) => [d.lng, d.lat],
    getRadius: 3000,
    getFillColor: [70, 140, 255, 180],
    radiusMinPixels: 2,
    radiusMaxPixels: 8,
    stroked: true,
    getLineColor: [100, 170, 255, 160],
    getLineWidth: 1,
    lineWidthMinPixels: 1,
    pickable: true,
    updateTriggers: {
      getPosition: [airports.length],
    },
  });
}

/**
 * Military base layer — red triangle-like markers (rendered as small red dots
 * with a distinctive stroke to differentiate from other markers).
 */
export function createMilitaryBaseLayer(bases: ReferencePoint[]) {
  if (!bases || bases.length === 0) {
    return new ScatterplotLayer<ReferencePoint>({
      id: 'military-bases',
      data: [],
      getPosition: () => [0, 0],
      visible: false,
    });
  }

  return new ScatterplotLayer<ReferencePoint>({
    id: 'military-bases',
    data: bases,
    getPosition: (d) => [d.lng, d.lat],
    getRadius: 5000,
    getFillColor: [200, 30, 30, 200],
    radiusMinPixels: 4,
    radiusMaxPixels: 14,
    stroked: true,
    getLineColor: [255, 80, 80, 220],
    getLineWidth: 2,
    lineWidthMinPixels: 1,
    pickable: true,
    updateTriggers: {
      getPosition: [bases.length],
    },
  });
}

/**
 * Datacenter layer — green dots.
 */
export function createDatacenterLayer(dcs: ReferencePoint[]) {
  if (!dcs || dcs.length === 0) {
    return new ScatterplotLayer<ReferencePoint>({
      id: 'datacenters',
      data: [],
      getPosition: () => [0, 0],
      visible: false,
    });
  }

  return new ScatterplotLayer<ReferencePoint>({
    id: 'datacenters',
    data: dcs,
    getPosition: (d) => [d.lng, d.lat],
    getRadius: 3500,
    getFillColor: [50, 200, 80, 180],
    radiusMinPixels: 3,
    radiusMaxPixels: 10,
    stroked: true,
    getLineColor: [80, 230, 110, 160],
    getLineWidth: 1,
    lineWidthMinPixels: 1,
    pickable: true,
    updateTriggers: {
      getPosition: [dcs.length],
    },
  });
}

/**
 * KiwiSDR layer — purple dots for software-defined radio receivers.
 */
export function createKiwiSDRLayer(sdrs: KiwiSDR[]) {
  if (!sdrs || sdrs.length === 0) {
    return new ScatterplotLayer<KiwiSDR>({
      id: 'kiwisdr',
      data: [],
      getPosition: () => [0, 0],
      visible: false,
    });
  }

  return new ScatterplotLayer<KiwiSDR>({
    id: 'kiwisdr',
    data: sdrs,
    getPosition: (d) => [d.lng, d.lat],
    getRadius: 4000,
    getFillColor: [160, 80, 220, 180],
    radiusMinPixels: 3,
    radiusMaxPixels: 10,
    stroked: true,
    getLineColor: [190, 120, 255, 160],
    getLineWidth: 1,
    lineWidthMinPixels: 1,
    pickable: true,
    updateTriggers: {
      getPosition: [sdrs.length],
    },
  });
}
