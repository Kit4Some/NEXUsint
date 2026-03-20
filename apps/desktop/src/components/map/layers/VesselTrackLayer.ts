import { TripsLayer } from '@deck.gl/geo-layers';
import { IconLayer } from '@deck.gl/layers';
import type { TrackPoint } from '@/types';

const VESSEL_COLOR: [number, number, number] = [32, 178, 170]; // Teal

interface VesselTrack {
  entityId: string;
  vesselName: string;
  points: TrackPoint[];
}

export function createVesselTrackLayer(
  tracks: VesselTrack[],
  currentTime: number,
) {
  const tripsData = tracks.map((track) => ({
    path: track.points.map((p) => [p.position.longitude, p.position.latitude]),
    timestamps: track.points.map((_, i) => i),
    entityId: track.entityId,
    vesselName: track.vesselName,
  }));

  const tripsLayer = new TripsLayer({
    id: 'vessel-tracks',
    data: tripsData,
    getPath: (d) => d.path,
    getTimestamps: (d) => d.timestamps,
    getColor: VESSEL_COLOR,
    opacity: 0.8,
    widthMinPixels: 2,
    trailLength: 30,
    currentTime,
  });

  const headPositions = tracks
    .filter((t) => t.points.length > 0)
    .map((track) => {
      const last = track.points[track.points.length - 1];
      return {
        position: [last.position.longitude, last.position.latitude] as [number, number],
        heading: last.heading ?? 0,
        vesselName: track.vesselName,
        entityId: track.entityId,
      };
    });

  const iconLayer = new IconLayer({
    id: 'vessel-icons',
    data: headPositions,
    getPosition: (d) => d.position,
    getAngle: (d) => 360 - d.heading,
    getSize: 18,
    getIcon: () => ({
      url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%2320b2aa"><path d="M12 2l-6 10h3v6h6v-6h3z"/></svg>',
      width: 24,
      height: 24,
      anchorY: 12,
    }),
    pickable: true,
  });

  return [tripsLayer, iconLayer];
}
