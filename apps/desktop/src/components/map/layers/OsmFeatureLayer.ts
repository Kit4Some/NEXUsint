import { GeoJsonLayer } from '@deck.gl/layers';

interface OsmFeature {
  type: 'Feature';
  geometry: {
    type: string;
    coordinates: number[] | number[][] | number[][][];
  };
  properties: {
    id: string;
    name?: string;
    tags?: Record<string, string>;
    feature_type?: string;
  };
}

interface OsmFeatureCollection {
  type: 'FeatureCollection';
  features: OsmFeature[];
}

/**
 * Deck.gl GeoJsonLayer for OSM features (buildings, roads, POIs).
 */
export function createOsmFeatureLayer(
  data: OsmFeatureCollection | null,
  visible: boolean,
  onClick?: (info: { object?: OsmFeature }) => void,
) {
  return new GeoJsonLayer({
    id: 'osm-feature-layer',
    data: data ?? { type: 'FeatureCollection' as const, features: [] },
    visible,
    pickable: true,
    stroked: true,
    filled: true,
    pointRadiusMinPixels: 4,
    pointRadiusScale: 10,
    lineWidthMinPixels: 1,
    getFillColor: [0, 180, 230, 100],
    getLineColor: [0, 180, 230, 200],
    getPointRadius: 5,
    getLineWidth: 1,
    onClick: onClick as never,
  });
}

export type { OsmFeature, OsmFeatureCollection };
