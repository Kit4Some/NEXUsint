/**
 * Geospatial utility functions for NEXUS OSINT.
 */

import type { TrackPoint } from '@/types';

/**
 * Ray-casting point-in-polygon test.
 */
export function pointInPolygon(
  point: [number, number],
  polygon: [number, number][],
): boolean {
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

/**
 * Interpolate position along a track at a given normalized progress (0-1).
 */
export function interpolateTrackPosition(
  points: TrackPoint[],
  progress: number,
): { longitude: number; latitude: number; altitude?: number } | null {
  if (points.length === 0) return null;
  if (points.length === 1) return points[0].position;

  const clampedProgress = Math.max(0, Math.min(1, progress));
  const idx = clampedProgress * (points.length - 1);
  const lower = Math.floor(idx);
  const upper = Math.min(lower + 1, points.length - 1);
  const t = idx - lower;

  const p0 = points[lower].position;
  const p1 = points[upper].position;

  return {
    longitude: p0.longitude + (p1.longitude - p0.longitude) * t,
    latitude: p0.latitude + (p1.latitude - p0.latitude) * t,
    altitude: (p0.altitude || 0) + ((p1.altitude || 0) - (p0.altitude || 0)) * t,
  };
}

/**
 * Format seconds as MM:SS or HH:MM:SS string.
 */
export function formatPlaybackTime(seconds: number): string {
  const s = Math.floor(Math.max(0, seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  if (h > 0) return `${pad(h)}:${pad(m)}:${pad(sec)}`;
  return `${pad(m)}:${pad(sec)}`;
}

/**
 * Approximate MGRS string generator for UI simulation.
 * (Actual MGRS requires complex projection math. This generates a visually correct MGRS string structure based on Lat/Lng)
 */
export function toMGRS(lat: number, lon: number): string {
  // Simple heuristic for generic MGRS string format "4QFJ 12345 67890"
  const utmZone = Math.floor((lon + 180) / 6) + 1;
  const latBands = 'CDEFGHJKLMNPQRSTUVWX';
  const latBand = latBands.charAt(Math.floor((lat + 80) / 8)) || 'Z';

  // Fake 100km square
  const e100k = String.fromCharCode(65 + (Math.floor(Math.abs(lon * 10)) % 24));
  const n100k = String.fromCharCode(65 + (Math.floor(Math.abs(lat * 10)) % 20));

  // 5-digit easting/northing
  const easting = Math.floor((Math.abs(lon) % 1) * 100000).toString().padStart(5, '0');
  const northing = Math.floor((Math.abs(lat) % 1) * 100000).toString().padStart(5, '0');

  return `${utmZone}${latBand}${e100k}${n100k} ${easting} ${northing}`;
}
