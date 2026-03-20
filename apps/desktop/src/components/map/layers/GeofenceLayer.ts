import { GeoJsonLayer } from '@deck.gl/layers';
import type { Feature, Polygon } from 'geojson';

export interface Geofence {
  id: string;
  name: string;
  polygon: Feature<Polygon>;
  alertType: 'entry' | 'exit' | 'both';
}

export function createGeofenceLayer(
  geofences: Geofence[],
  visible: boolean,
  editingId: string | null,
) {
  const features = geofences.map((g) => ({
    ...g.polygon,
    properties: {
      ...g.polygon.properties,
      id: g.id,
      name: g.name,
      alertType: g.alertType,
      isEditing: g.id === editingId,
    },
  }));

  return new GeoJsonLayer({
    id: 'geofence-layer',
    data: { type: 'FeatureCollection' as const, features },
    visible,
    pickable: true,
    stroked: true,
    filled: true,
    getFillColor: (f: { properties?: { isEditing?: boolean } }) =>
      f.properties?.isEditing
        ? [255, 184, 0, 40]   // amber while editing
        : [0, 212, 255, 25],  // cyan fill
    getLineColor: (f: { properties?: { isEditing?: boolean } }) =>
      f.properties?.isEditing
        ? [255, 184, 0, 200]
        : [0, 212, 255, 150],
    getLineWidth: 2,
    lineWidthMinPixels: 1,
  });
}
