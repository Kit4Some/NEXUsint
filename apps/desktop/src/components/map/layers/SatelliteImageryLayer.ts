import { PolygonLayer } from '@deck.gl/layers';

interface SatelliteFootprint {
  id: string;
  name: string;
  bbox: [number, number, number, number]; // [west, south, east, north]
  cloud_cover: number;
  date: string;
}

/**
 * Deck.gl PolygonLayer for satellite image footprints.
 * Color-coded by cloud cover: green (low) → yellow → red (high).
 */
export function createSatelliteImageryLayer(
  data: SatelliteFootprint[],
  visible: boolean,
  onClick?: (info: { object?: SatelliteFootprint }) => void,
) {
  return new PolygonLayer<SatelliteFootprint>({
    id: 'satellite-imagery-layer',
    data,
    visible,
    pickable: true,
    stroked: true,
    filled: true,
    wireframe: false,
    lineWidthMinPixels: 1,
    getPolygon: (d) => {
      const [west, south, east, north] = d.bbox;
      return [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
      ];
    },
    getFillColor: (d) => cloudCoverColor(d.cloud_cover),
    getLineColor: [100, 200, 255, 200],
    getLineWidth: 1,
    onClick: onClick as never,
    updateTriggers: {
      getFillColor: [data],
    },
  });
}

function cloudCoverColor(cloudCover: number): [number, number, number, number] {
  // 0% cloud → green, 50% → yellow, 100% → red
  const t = Math.min(1, Math.max(0, cloudCover / 100));
  if (t < 0.5) {
    const s = t * 2;
    return [Math.round(s * 255), 255, 0, 80];
  }
  const s = (t - 0.5) * 2;
  return [255, Math.round((1 - s) * 255), 0, 80];
}

export type { SatelliteFootprint };
