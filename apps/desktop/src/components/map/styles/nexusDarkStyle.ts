/**
 * Custom MapLibre style: dark basemap + high-zoom detail (roads, buildings, POI).
 * Combines CartoDB dark raster tiles with OpenMapTiles vector overlays.
 */

export function createNexusMapStyle(): Record<string, unknown> {
  return {
    version: 8,
    name: 'NEXUS Dark',
    glyphs: 'https://fonts.openmaptiles.org/{fontstack}/{range}.pbf',
    sources: {
      'carto-dark': {
        type: 'raster',
        tiles: ['https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png'],
        tileSize: 256,
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
        maxzoom: 20,
      },
      openmaptiles: {
        type: 'vector',
        tiles: ['https://tiles.stadiamaps.com/data/openmaptiles/{z}/{x}/{y}.pbf'],
        maxzoom: 14,
        attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a>',
      },
    },
    layers: [
      // Base dark raster — always visible
      {
        id: 'dark-base',
        type: 'raster',
        source: 'carto-dark',
        paint: { 'raster-opacity': 1 },
      },

      // ─── Water (zoom ≥ 12) ────────────────────────────────
      {
        id: 'water',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'water',
        minzoom: 12,
        paint: {
          'fill-color': 'rgba(10, 15, 30, 0.8)',
          'fill-outline-color': 'rgba(20, 40, 70, 0.5)',
        },
      },

      // ─── Roads (zoom ≥ 14) ────────────────────────────────
      {
        id: 'roads-highway',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        minzoom: 13,
        filter: ['in', 'class', 'motorway', 'trunk', 'primary'],
        paint: {
          'line-color': 'rgba(50, 65, 90, 0.7)',
          'line-width': ['interpolate', ['linear'], ['zoom'], 13, 1, 16, 4, 20, 10],
        },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      },
      {
        id: 'roads-secondary',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        minzoom: 14,
        filter: ['in', 'class', 'secondary', 'tertiary'],
        paint: {
          'line-color': 'rgba(45, 55, 80, 0.6)',
          'line-width': ['interpolate', ['linear'], ['zoom'], 14, 0.5, 16, 2, 20, 6],
        },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      },
      {
        id: 'roads-minor',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        minzoom: 15,
        filter: ['in', 'class', 'minor', 'service', 'path'],
        paint: {
          'line-color': 'rgba(40, 50, 70, 0.5)',
          'line-width': ['interpolate', ['linear'], ['zoom'], 15, 0.3, 18, 1.5, 20, 3],
        },
      },

      // ─── Buildings 2D (zoom ≥ 15) ─────────────────────────
      {
        id: 'buildings',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'building',
        minzoom: 15,
        paint: {
          'fill-color': 'rgba(25, 35, 55, 0.8)',
          'fill-outline-color': 'rgba(45, 60, 85, 0.9)',
        },
      },

      // ─── Buildings 3D extrusion (zoom ≥ 16) ───────────────
      {
        id: 'buildings-3d',
        type: 'fill-extrusion',
        source: 'openmaptiles',
        'source-layer': 'building',
        minzoom: 16,
        paint: {
          'fill-extrusion-color': [
            'interpolate', ['linear'], ['coalesce', ['get', 'render_height'], 8],
            0, 'rgba(15, 20, 35, 0.9)',
            20, 'rgba(22, 40, 60, 0.85)',
            100, 'rgba(0, 150, 255, 0.5)',
            300, 'rgba(0, 255, 255, 0.6)'
          ],
          'fill-extrusion-height': [
            'interpolate', ['linear'], ['zoom'],
            16, 0,
            16.5, ['coalesce', ['get', 'render_height'], 8],
          ],
          'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0],
          'fill-extrusion-opacity': 0.85,
        },
      },

      // ─── Road labels (zoom ≥ 15) ──────────────────────────
      {
        id: 'road-labels',
        type: 'symbol',
        source: 'openmaptiles',
        'source-layer': 'transportation_name',
        minzoom: 15,
        layout: {
          'text-field': '{name}',
          'text-font': ['Open Sans Regular'],
          'text-size': ['interpolate', ['linear'], ['zoom'], 15, 9, 18, 12],
          'symbol-placement': 'line',
          'text-max-angle': 30,
          'text-padding': 2,
        },
        paint: {
          'text-color': 'rgba(140, 155, 180, 0.8)',
          'text-halo-color': 'rgba(10, 14, 25, 0.9)',
          'text-halo-width': 1.5,
        },
      },

      // ─── Place labels (zoom ≥ 10) ─────────────────────────
      {
        id: 'place-labels',
        type: 'symbol',
        source: 'openmaptiles',
        'source-layer': 'place',
        minzoom: 10,
        layout: {
          'text-field': '{name}',
          'text-font': ['Open Sans Regular'],
          'text-size': [
            'interpolate', ['linear'], ['zoom'],
            10, ['match', ['get', 'class'], 'city', 14, 'town', 12, 10],
            16, ['match', ['get', 'class'], 'city', 20, 'town', 16, 12],
          ],
          'text-max-width': 10,
        },
        paint: {
          'text-color': 'rgba(160, 175, 200, 0.9)',
          'text-halo-color': 'rgba(10, 14, 25, 0.95)',
          'text-halo-width': 2,
        },
      },

      // ─── POI labels (zoom ≥ 16) ───────────────────────────
      {
        id: 'poi-labels',
        type: 'symbol',
        source: 'openmaptiles',
        'source-layer': 'poi',
        minzoom: 16,
        layout: {
          'text-field': '{name}',
          'text-font': ['Open Sans Regular'],
          'text-size': 10,
          'text-max-width': 8,
          'text-anchor': 'top',
          'text-offset': [0, 0.6],
        },
        paint: {
          'text-color': 'rgba(100, 180, 220, 0.7)',
          'text-halo-color': 'rgba(10, 14, 25, 0.9)',
          'text-halo-width': 1,
        },
      },
    ],
  };
}
