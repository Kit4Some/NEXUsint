/**
 * Entity type icon definitions + GPU-optimized icon atlas builder.
 * 22 entity types → individual SVG paths → single Canvas atlas for deck.gl IconLayer.
 */

export interface EntityIconDef {
  /** SVG path data (d attribute) — viewBox 0 0 24 24 */
  path: string;
  /** RGB color */
  color: [number, number, number];
  /** Intelligence category */
  category: 'CYBINT' | 'SOCMINT' | 'SIGINT' | 'GEOINT' | 'GENERAL';
  /** Whether the icon should rotate based on heading (Aircraft/Vessel) */
  rotatable: boolean;
}

export const ENTITY_ICON_MAP: Record<string, EntityIconDef> = {
  // ─── CYBINT ───────────────────────────────────────────────
  IPAddress: {
    // Crosshair / network node
    path: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 2a8 8 0 1 1 0 16 8 8 0 0 1 0-16zm-1 3v3H8v2h3v3h2v-3h3v-2h-3V7h-2z',
    color: [255, 51, 102],
    category: 'CYBINT',
    rotatable: false,
  },
  Domain: {
    // Globe with grid
    path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z',
    color: [0, 255, 136],
    category: 'CYBINT',
    rotatable: false,
  },
  ThreatActor: {
    // Hooded figure
    path: 'M12 2C9.24 2 7 4.24 7 7c0 1.64.8 3.09 2.03 4H9c-2.76 0-5 2.24-5 5v2h4v-2c0-.55.45-1 1-1h6c.55 0 1 .45 1 1v2h4v-2c0-2.76-2.24-5-5-5h-.03A4.98 4.98 0 0 0 17 7c0-2.76-2.24-5-5-5zm0 2c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3z',
    color: [255, 184, 0],
    category: 'CYBINT',
    rotatable: false,
  },
  Malware: {
    // Bug / virus
    path: 'M20 8h-2.81a5.99 5.99 0 0 0-1.82-2.43l1.34-1.34-1.42-1.42-1.63 1.63A5.9 5.9 0 0 0 12 4c-.58 0-1.14.08-1.66.24L8.71 2.61 7.29 4.03l1.34 1.34A5.99 5.99 0 0 0 6.81 8H4v2h2.09c-.06.33-.09.66-.09 1v1H4v2h2v1c0 .34.03.67.09 1H4v2h2.81a6 6 0 0 0 10.38 0H20v-2h-2.09c.06-.33.09-.66.09-1v-1h2v-2h-2v-1c0-.34-.03-.67-.09-1H20V8zm-6 8h-4v-2h4v2zm0-4h-4v-2h4v2z',
    color: [255, 70, 70],
    category: 'CYBINT',
    rotatable: false,
  },
  Vulnerability: {
    // Broken shield
    path: 'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18l7 3.12v4.7c0 4.83-3.4 9.36-7 10.58V3.18zm-7 3.12l7-3.12V6l-3 1v3l-2-1v4l5 3v4.58C7.4 19.36 5 15.33 5 11V6.3z',
    color: [255, 120, 50],
    category: 'CYBINT',
    rotatable: false,
  },
  Certificate: {
    // Seal / stamp
    path: 'M12 1l-2.4 3.2L6 3.6l-.6 3.6-3.2 2.4L3.6 13 1 15.4l2.4 2.4-.6 3.6 3.6.6L9 24l3-1.2 3 1.2 2.4-2.4 3.6-.6-.6-3.6L22 15.4 20.4 13l1.4-3.4L19.4 7l-.6-3.6-3.6-.6L12 1zm0 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14zm-1.5 3.5v3h-2v2h2v3h3v-3h2v-2h-2v-3h-3z',
    color: [180, 180, 180],
    category: 'CYBINT',
    rotatable: false,
  },
  Indicator: {
    // Warning triangle
    path: 'M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z',
    color: [255, 200, 50],
    category: 'CYBINT',
    rotatable: false,
  },

  // ─── SOCMINT ──────────────────────────────────────────────
  Person: {
    // Person silhouette
    path: 'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z',
    color: [0, 150, 255],
    category: 'SOCMINT',
    rotatable: false,
  },
  SocialAccount: {
    // Person with @ symbol
    path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10h5v-2h-5c-4.34 0-8-3.66-8-8s3.66-8 8-8 8 3.66 8 8v1.43c0 .79-.71 1.57-1.5 1.57s-1.5-.78-1.5-1.57V12c0-2.76-2.24-5-5-5s-5 2.24-5 5 2.24 5 5 5c1.38 0 2.64-.56 3.54-1.47.65.89 1.77 1.47 2.96 1.47 1.97 0 3.5-1.6 3.5-3.57V12c0-5.52-4.48-10-10-10zm0 13c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3z',
    color: [100, 130, 255],
    category: 'SOCMINT',
    rotatable: false,
  },
  Post: {
    // Chat bubble
    path: 'M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z',
    color: [160, 120, 255],
    category: 'SOCMINT',
    rotatable: false,
  },
  Hashtag: {
    // # symbol
    path: 'M5.41 21L6.12 17H2.12L2.47 15H6.47L7.53 9H3.53L3.88 7H7.88L8.59 3H10.59L9.88 7H15.88L16.59 3H18.59L17.88 7H21.88L21.53 9H17.53L16.47 15H20.47L20.12 17H16.12L15.41 21H13.41L14.12 17H8.12L7.41 21H5.41ZM9.53 9L8.47 15H14.47L15.53 9H9.53Z',
    color: [180, 100, 255],
    category: 'SOCMINT',
    rotatable: false,
  },
  Organization: {
    // Building
    path: 'M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z',
    color: [130, 80, 255],
    category: 'SOCMINT',
    rotatable: false,
  },

  // ─── SIGINT ───────────────────────────────────────────────
  Aircraft: {
    // Top-down aircraft (rotatable)
    path: 'M12 2L10 8H4l-2 3h8l-1 7-3 2v2l6-2 6 2v-2l-3-2-1-7h8l-2-3h-6L12 2z',
    color: [255, 107, 53],
    category: 'SIGINT',
    rotatable: true,
  },
  Vessel: {
    // Top-down vessel (rotatable)
    path: 'M12 2l-3 8H5l-1 2h5v6l-3 2.5L7.5 22h9L18 20.5 15 18v-6h5l-1-2h-4L12 2zm0 3l2 6h-4l2-6z',
    color: [32, 178, 170],
    category: 'SIGINT',
    rotatable: true,
  },
  FlightPath: {
    // Dashed arc line
    path: 'M3.5 18.5l3-3c1.5-1.5 3.5-2 5.5-2s4 .5 5.5 2l3 3M5 15l2-4c1-2 3-3 5-3s4 1 5 3l2 4M8 8a8 8 0 0 1 8 0',
    color: [255, 140, 80],
    category: 'SIGINT',
    rotatable: false,
  },
  VoyageTrack: {
    // Wave line
    path: 'M2 12c1.5-2 3-3 4.5-1.5S10 13 12 12s2-3 4.5-1.5S20 14 22 12M2 17c1.5-2 3-3 4.5-1.5S10 18 12 17s2-3 4.5-1.5S20 19 22 17M2 7c1.5-2 3-3 4.5-1.5S10 8 12 7s2-3 4.5-1.5S20 9 22 7',
    color: [80, 200, 190],
    category: 'SIGINT',
    rotatable: false,
  },

  // ─── GEOINT ───────────────────────────────────────────────
  Location: {
    // Map pin marker
    path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 0 1 0-5 2.5 2.5 0 0 1 0 5z',
    color: [0, 212, 255],
    category: 'GEOINT',
    rotatable: false,
  },
  SatelliteImage: {
    // Satellite with orbit
    path: 'M6.05 4.14l-1.41 1.41 3.13 3.13a4.02 4.02 0 0 0 0 4.64l-3.13 3.13 1.41 1.41 3.13-3.13a4.02 4.02 0 0 0 4.64 0l3.13 3.13 1.41-1.41-3.13-3.13a4.02 4.02 0 0 0 0-4.64l3.13-3.13-1.41-1.41-3.13 3.13a4.02 4.02 0 0 0-4.64 0L6.05 4.14zM12 10a2 2 0 1 1 0 4 2 2 0 0 1 0-4z',
    color: [50, 220, 180],
    category: 'GEOINT',
    rotatable: false,
  },
  GeoFeature: {
    // Mountain profile
    path: 'M14 6l-3.75 5L7 7l-6 10h22L14 6zm-4.75 8L7 10.33 4.75 14h4.5zm5.25-1.5l3.5 5.5H11l3.5-5.5z',
    color: [60, 200, 150],
    category: 'GEOINT',
    rotatable: false,
  },
  GeoFence: {
    // Dotted boundary / perimeter
    path: 'M3 3v18h18V3H3zm16 16H5V5h14v14zM7 7h2v2H7V7zm4 0h2v2h-2V7zm4 0h2v2h-2V7zm-8 4h2v2H7v-2zm8 0h2v2h-2v-2zm-8 4h2v2H7v-2zm4 0h2v2h-2v-2zm4 0h2v2h-2v-2z',
    color: [220, 220, 100],
    category: 'GEOINT',
    rotatable: false,
  },

  // ─── GENERAL ──────────────────────────────────────────────
  Event: {
    // Lightning bolt
    path: 'M7 2v11h3v9l7-12h-4l4-8H7z',
    color: [200, 200, 200],
    category: 'GENERAL',
    rotatable: false,
  },
  Object: {
    // Cube
    path: 'M21 16.5c0 .38-.21.71-.53.88l-7.9 4.44c-.36.2-.8.2-1.14 0l-7.9-4.44A.99.99 0 0 1 3 16.5v-9c0-.38.21-.71.53-.88l7.9-4.44c.36-.2.8-.2 1.14 0l7.9 4.44c.32.17.53.5.53.88v9zM12 4.15L5 8.09v7.82l7 3.94 7-3.94V8.09l-7-3.94z',
    color: [150, 150, 150],
    category: 'GENERAL',
    rotatable: false,
  },
};

/** Default icon for unknown types */
const DEFAULT_ICON: EntityIconDef = {
  path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z',
  color: [100, 100, 100],
  category: 'GENERAL',
  rotatable: false,
};

/** Get icon definition for an entity type, with fallback */
export function getEntityIcon(type: string): EntityIconDef {
  return ENTITY_ICON_MAP[type] || DEFAULT_ICON;
}

/** Get color for an entity type */
export function getEntityColor(type: string): [number, number, number] {
  return (ENTITY_ICON_MAP[type] || DEFAULT_ICON).color;
}

// ─── Icon Atlas Builder ─────────────────────────────────────
// Renders all icons onto a single Canvas → uploaded as one GPU texture.
// deck.gl IconLayer consumes this via `iconAtlas` + `iconMapping`.

const ICON_SIZE = 64;
const COLS = 6;

/** All icon keys in stable order */
const ICON_KEYS = Object.keys(ENTITY_ICON_MAP);

type IconMapping = Record<string, { x: number; y: number; width: number; height: number; anchorY: number }>;

let _cachedAtlas: HTMLCanvasElement | null = null;
let _cachedMapping: IconMapping | null = null;

export function createEntityIconAtlas(): { atlas: HTMLCanvasElement; mapping: IconMapping } {
  if (_cachedAtlas && _cachedMapping) {
    return { atlas: _cachedAtlas, mapping: _cachedMapping };
  }

  const rows = Math.ceil((ICON_KEYS.length + 1) / COLS); // +1 for default
  const allKeys = [...ICON_KEYS, '_default'];
  const width = COLS * ICON_SIZE;
  const height = rows * ICON_SIZE;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d')!;

  const mapping: IconMapping = {};

  allKeys.forEach((key, idx) => {
    const col = idx % COLS;
    const row = Math.floor(idx / COLS);
    const x = col * ICON_SIZE;
    const y = row * ICON_SIZE;

    const def = key === '_default' ? DEFAULT_ICON : ENTITY_ICON_MAP[key];
    if (!def) return;

    // Draw SVG path onto canvas via Path2D
    const pad = 8;
    const drawSize = ICON_SIZE - pad * 2;
    ctx.save();
    ctx.translate(x + pad, y + pad);
    ctx.scale(drawSize / 24, drawSize / 24);

    const path2d = new Path2D(def.path);
    ctx.fillStyle = `rgb(${def.color[0]},${def.color[1]},${def.color[2]})`;
    ctx.fill(path2d);

    ctx.restore();

    mapping[key] = { x, y, width: ICON_SIZE, height: ICON_SIZE, anchorY: ICON_SIZE / 2 };
  });

  _cachedAtlas = canvas;
  _cachedMapping = mapping;

  return { atlas: canvas, mapping };
}

/** Get SVG data URI for inline display (popups, UI) */
export function getEntityIconSvgUri(type: string, size = 24): string {
  const def = ENTITY_ICON_MAP[type] || DEFAULT_ICON;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}"><path d="${def.path}" fill="rgb(${def.color[0]},${def.color[1]},${def.color[2]})"/></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
