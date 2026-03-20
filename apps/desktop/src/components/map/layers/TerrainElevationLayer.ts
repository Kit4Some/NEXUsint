import { TerrainLayer } from '@deck.gl/geo-layers';

// AWS open terrain tiles (Terrarium encoding, free, no API key)
const ELEVATION_URL =
  'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png';
const SURFACE_URL =
  'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png';

const TERRARIUM_DECODER = {
  rScaler: 256,
  gScaler: 1,
  bScaler: 1 / 256,
  offset: -32768,
};

export function createTerrainElevationLayer(visible: boolean, zoom: number) {
  if (!visible || zoom < 10) return null;

  return new TerrainLayer({
    id: 'terrain-elevation',
    elevationData: ELEVATION_URL,
    texture: SURFACE_URL,
    elevationDecoder: TERRARIUM_DECODER,
    meshMaxError: zoom > 14 ? 1 : 4,
    minZoom: 0,
    maxZoom: 15,
    material: {
      ambient: 0.3,
      diffuse: 0.8,
      shininess: 10,
    },
    opacity: 0.9,
  });
}
