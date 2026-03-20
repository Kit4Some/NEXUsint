import { ScatterplotLayer } from '@deck.gl/layers';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';
import { TileLayer } from '@deck.gl/geo-layers';
import { BitmapLayer } from '@deck.gl/layers';
import type { PickingInfo } from '@deck.gl/core';
import type { Earthquake, FireHotspot, WeatherRadar } from '@/types/livefeed';

// --- Earthquake layer ---

function getEarthquakeColor(mag: number): [number, number, number, number] {
  if (mag >= 7) return [255, 40, 40, 220];
  if (mag >= 5) return [255, 140, 40, 200];
  return [255, 220, 60, 180];
}

function getEarthquakeRadius(mag: number): number {
  return Math.max(mag, 1) * 5000;
}

export function createEarthquakeLayer(
  quakes: Earthquake[],
  onClick?: (info: PickingInfo) => void,
) {
  return new ScatterplotLayer<Earthquake>({
    id: 'earthquakes',
    data: quakes,
    getPosition: (d) => [d.lng, d.lat],
    getFillColor: (d) => getEarthquakeColor(d.mag),
    getLineColor: (d) => {
      const c = getEarthquakeColor(d.mag);
      return [c[0], c[1], c[2], 255] as [number, number, number, number];
    },
    getRadius: (d) => getEarthquakeRadius(d.mag),
    radiusMinPixels: 4,
    radiusMaxPixels: 60,
    stroked: true,
    filled: true,
    lineWidthMinPixels: 1,
    pickable: true,
    antialiasing: true,
    onClick: onClick ?? undefined,
    updateTriggers: {
      getPosition: [quakes.length],
      getFillColor: [quakes.length],
      getRadius: [quakes.length],
    },
  });
}

// --- Fire hotspot heatmap ---

export function createFireLayer(fires: FireHotspot[]) {
  return new HeatmapLayer<FireHotspot>({
    id: 'fire-hotspots',
    data: fires,
    getPosition: (d) => [d.lng, d.lat],
    getWeight: (d) => d.frp || 1,
    radiusPixels: 40,
    intensity: 1.2,
    threshold: 0.1,
    colorRange: [
      [255, 255, 178],
      [254, 204, 92],
      [253, 141, 60],
      [240, 59, 32],
      [189, 0, 38],
      [128, 0, 38],
    ],
    aggregation: 'SUM',
    pickable: false,
    updateTriggers: {
      getPosition: [fires.length],
      getWeight: [fires.length],
    },
  });
}

// --- Weather radar tile layer (RainViewer) ---

export function createWeatherRadarLayer(radar: WeatherRadar | null) {
  if (!radar || !radar.host || !radar.time) {
    return null;
  }

  return new TileLayer({
    id: 'weather-radar',
    data: `${radar.host}/v2/radar/${radar.time}/256/{z}/{x}/{y}/2/1_1.png`,
    minZoom: 0,
    maxZoom: 12,
    tileSize: 256,
    opacity: 0.5,
    renderSubLayers: (props) => {
      const { boundingBox } = props.tile;
      return new BitmapLayer(props, {
        data: undefined,
        image: props.data,
        bounds: [
          boundingBox[0][0],
          boundingBox[0][1],
          boundingBox[1][0],
          boundingBox[1][1],
        ],
      });
    },
    pickable: false,
  });
}
