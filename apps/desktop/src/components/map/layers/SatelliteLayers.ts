import { ScatterplotLayer } from '@deck.gl/layers';
import type { Satellite } from '@/types/livefeed';

/**
 * Create a Deck.gl layer for satellite positions.
 * Renders white/yellow dots sized by altitude. Higher satellites appear larger.
 */
export function createSatelliteLayer(
  satellites: Satellite[],
  onClick?: (info: any) => void,
) {
  if (!satellites || satellites.length === 0) {
    return new ScatterplotLayer<Satellite>({
      id: 'satellites',
      data: [],
      getPosition: () => [0, 0],
      visible: false,
    });
  }

  // Altitude normalization: LEO ~200-2000km, MEO ~2000-35786km, GEO ~35786km
  const maxAlt = Math.max(...satellites.map((s) => s.alt), 1);

  return new ScatterplotLayer<Satellite>({
    id: 'satellites',
    data: satellites,
    getPosition: (d) => [d.lng, d.lat],
    getRadius: (d) => {
      // Scale radius by altitude — higher orbits get bigger dots
      const normalized = Math.min(d.alt / maxAlt, 1);
      return 4000 + normalized * 20000;
    },
    getFillColor: (d) => {
      // LEO satellites: white, GEO/MEO: yellow tint
      if (d.alt > 10000) {
        return [255, 230, 100, 200]; // yellow
      }
      return [240, 240, 255, 200]; // white
    },
    radiusMinPixels: 2,
    radiusMaxPixels: 10,
    stroked: true,
    getLineColor: (d) => {
      if (d.alt > 10000) {
        return [255, 200, 50, 160];
      }
      return [200, 200, 255, 160];
    },
    getLineWidth: 1,
    lineWidthMinPixels: 1,
    pickable: true,
    onClick: onClick
      ? (info) => {
          if (info.object) onClick(info);
        }
      : undefined,
    updateTriggers: {
      getPosition: [satellites.length],
      getFillColor: [satellites.length],
    },
  });
}
