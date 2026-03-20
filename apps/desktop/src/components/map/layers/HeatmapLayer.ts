import { HeatmapLayer as DeckHeatmapLayer } from '@deck.gl/aggregation-layers';

interface HeatmapPoint {
  position: [number, number];
  weight: number;
}

export function createHeatmapLayer(data: HeatmapPoint[], visible: boolean) {
  return new DeckHeatmapLayer<HeatmapPoint>({
    id: 'heatmap-layer',
    data,
    visible,
    getPosition: (d) => d.position,
    getWeight: (d) => d.weight,
    radiusPixels: 30,
    intensity: 1,
    threshold: 0.05,
    colorRange: [
      [1, 32, 128],    // deep blue
      [0, 212, 255],   // cyan
      [0, 255, 136],   // green
      [255, 184, 0],   // amber
      [255, 51, 102],  // red
      [220, 38, 38],   // dark red
    ],
    aggregation: 'SUM',
  });
}
