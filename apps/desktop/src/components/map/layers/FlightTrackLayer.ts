import { TripsLayer } from '@deck.gl/geo-layers';
import { IconLayer } from '@deck.gl/layers';
import type { TrackPoint } from '@/types';

const FLIGHT_COLOR: [number, number, number] = [255, 107, 53]; // Orange

interface FlightTrack {
  entityId: string;
  callsign: string;
  points: TrackPoint[];
}

export function createFlightTrackLayer(
  tracks: FlightTrack[],
  currentTime: number,
) {
  const tripsData = tracks.map((track) => ({
    path: track.points.map((p) => [
      p.position.longitude,
      p.position.latitude,
      p.position.altitude ?? 0,
    ]),
    timestamps: track.points.map((_, i) => i),
    entityId: track.entityId,
    callsign: track.callsign,
  }));

  const tripsLayer = new TripsLayer({
    id: 'flight-tracks',
    data: tripsData,
    getPath: (d) => d.path,
    getTimestamps: (d) => d.timestamps,
    getColor: FLIGHT_COLOR,
    opacity: 0.8,
    widthMinPixels: 2,
    trailLength: 20,
    currentTime,
  });

  // Aircraft icons at current positions
  const headPositions = tracks
    .filter((t) => t.points.length > 0)
    .map((track) => {
      const last = track.points[track.points.length - 1];
      return {
        position: [last.position.longitude, last.position.latitude] as [number, number],
        heading: last.heading ?? 0,
        callsign: track.callsign,
        entityId: track.entityId,
      };
    });

  const iconLayer = new IconLayer({
    id: 'flight-icons',
    data: headPositions,
    getPosition: (d) => d.position,
    getAngle: (d) => 360 - d.heading,
    getSize: 20,
    getIcon: () => ({
      url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23ff6b35"><path d="M12 2L4 14h4v8l8-12h-4z"/></svg>',
      width: 24,
      height: 24,
      anchorY: 12,
    }),
    pickable: true,
  });

  return [tripsLayer, iconLayer];
}
