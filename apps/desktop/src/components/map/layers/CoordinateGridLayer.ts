import { PathLayer } from '@deck.gl/layers';

export function createCoordinateGridLayer(
    visible: boolean,
    zoom: number,
    viewState: { longitude: number; latitude: number }
) {
    if (!visible || zoom < 14) return null;

    // Grid resolution based on zoom
    const step = zoom >= 17 ? 0.001 : zoom >= 15.5 ? 0.005 : 0.02;

    const spanLat = 180 / Math.pow(2, zoom);
    const spanLng = spanLat * 1.5;

    const minLat = Math.floor((viewState.latitude - spanLat) / step) * step;
    const maxLat = Math.ceil((viewState.latitude + spanLat) / step) * step;
    const minLng = Math.floor((viewState.longitude - spanLng) / step) * step;
    const maxLng = Math.ceil((viewState.longitude + spanLng) / step) * step;

    const lines = [];

    // Latitude lines
    for (let lat = minLat; lat <= maxLat; lat += step) {
        lines.push({
            path: [[minLng, lat], [maxLng, lat]],
            isMajor: Math.abs(lat % (step * 5)) < step * 0.1,
        });
    }

    // Longitude lines
    for (let lng = minLng; lng <= maxLng; lng += step) {
        lines.push({
            path: [[lng, minLat], [lng, maxLat]],
            isMajor: Math.abs(lng % (step * 5)) < step * 0.1,
        });
    }

    return new PathLayer({
        id: 'coordinate-grid-layer',
        data: lines,
        getPath: d => d.path,
        getColor: d => d.isMajor ? [0, 255, 255, 60] : [0, 150, 255, 25],
        getWidth: d => d.isMajor ? 2 : 1,
        widthMinPixels: 1,
        widthMaxPixels: 2,
        pickable: false,
        updateTriggers: {
            data: [minLat, maxLat, minLng, maxLng, step],
        }
    });
}
