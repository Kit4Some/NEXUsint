import { useCallback, useEffect, useMemo, useState } from 'react';
import { DeckGL } from '@deck.gl/react';
import { _GlobeView as GlobeViewDeck } from '@deck.gl/core';
import { ScatterplotLayer, ArcLayer, PathLayer, TextLayer, IconLayer, BitmapLayer, LineLayer } from '@deck.gl/layers';
import { TripsLayer, TileLayer } from '@deck.gl/geo-layers';
import MapGL from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useMapStore } from '@/stores/useMapStore';
import { useEntityStore } from '@/stores/useEntityStore';
import { map as mapApi } from '@/services/api';
import { interpolateTrackPosition } from '@/utils/geoUtils';
import { createEntityIconAtlas, getEntityColor } from './icons/entityIcons';
import { createNexusMapStyle } from './styles/nexusDarkStyle';
import { createTerrainElevationLayer } from './layers/TerrainElevationLayer';

function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

// Zoom thresholds for globe-to-map transition
const TRANSITION_START = 11;
const TRANSITION_END = 13;
const BUILDINGS_3D_ZOOM = 16;

interface GlobeEntityData {
  id: string;
  type: string;
  name: string;
  position: { latitude: number; longitude: number };
  confidence: number;
  sourceInt: string;
  riskScore: number;
}

export function GlobeView() {
  const {
    viewState, setViewState, visibleLayers, setSelectedEntityId,
    activeTracks, playbackTime, entityActivities,
    followEntityId, followMode, setFollowEntity, setFollowMode,
  } = useMapStore();
  const { setSelectedEntity } = useEntityStore();
  const [entities, setEntities] = useState<GlobeEntityData[]>([]);
  const [webglOk] = useState(() => isWebGLAvailable());
  const [deckError, setDeckError] = useState(false);

  // Icon atlas — memoized once (cast to any for deck.gl compatibility)
  const { atlas: iconAtlas, mapping: iconMapping } = useMemo(() => {
    const result = createEntityIconAtlas();
    return { atlas: result.atlas as any, mapping: result.mapping };
  }, []);

  // MapLibre style — memoized once
  const mapStyle = useMemo(() => createNexusMapStyle(), []);

  // Zoom-based transition progress (0 = pure globe, 1 = full MapLibre)
  const zoomProgress = useMemo(() => {
    const z = viewState.zoom;
    if (z <= TRANSITION_START) return 0;
    if (z >= TRANSITION_END) return 1;
    return (z - TRANSITION_START) / (TRANSITION_END - TRANSITION_START);
  }, [viewState.zoom]);

  // Current view mode label
  const viewModeLabel = useMemo(() => {
    if (viewState.zoom < TRANSITION_START) return 'GLOBE';
    if (viewState.zoom >= BUILDINGS_3D_ZOOM) return '3D';
    return 'STREET';
  }, [viewState.zoom]);

  const fetchEntities = useCallback(async () => {
    try {
      const data = await mapApi.getEntities({
        west: -180,
        south: -90,
        east: 180,
        north: 90,
      });
      setEntities(data as GlobeEntityData[]);
    } catch {
      // API not available
    }
  }, []);

  useEffect(() => {
    fetchEntities();
  }, [fetchEntities]);

  const globeView = new GlobeViewDeck({
    id: 'globe',
    controller: true,
    resolution: 10,
  });

  const layers: any[] = [];

  const terrainActive = visibleLayers.has('terrain');

  // Globe basemap — raster tiles on sphere surface (fades out at high zoom)
  if (!terrainActive || viewState.zoom < 10) {
    layers.push(
      new TileLayer({
        id: 'globe-basemap',
        data: 'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
        minZoom: 0,
        maxZoom: 19,
        tileSize: 256,
        opacity: 1 - zoomProgress,
        renderSubLayers: (props: any) => {
          const { boundingBox } = props.tile;
          return new BitmapLayer(props, {
            data: undefined,
            image: props.data,
            bounds: [
              boundingBox[0][0],
              boundingBox[0][1],
              boundingBox[1][0],
              boundingBox[1][1],
            ],
          });
        },
      }),
    );
  }

  // Terrain elevation layer (replaces flat basemap when active)
  if (terrainActive) {
    const terrainLayer = createTerrainElevationLayer(true, viewState.zoom);
    if (terrainLayer) layers.push(terrainLayer);
  }

  if (visibleLayers.has('entities')) {
    // Glow ring
    layers.push(
      new ScatterplotLayer<GlobeEntityData>({
        id: 'globe-entity-glow',
        data: entities,
        getPosition: (d) => [d.position.longitude, d.position.latitude],
        getRadius: 80000,
        getFillColor: (d) => {
          const c = getEntityColor(d.type);
          return [...c, Math.round(d.confidence * 60 + 20)] as [number, number, number, number];
        },
        radiusMinPixels: 4,
        radiusMaxPixels: 16,
        pickable: false,
      }),
    );

    // Icon layer — entity type SVG (billboard for globe)
    layers.push(
      new IconLayer<GlobeEntityData>({
        id: 'globe-entity-icon',
        data: entities,
        iconAtlas: iconAtlas,
        iconMapping: iconMapping,
        getIcon: (d) => (iconMapping[d.type] ? d.type : '_default'),
        getPosition: (d) => [d.position.longitude, d.position.latitude],
        getSize: (d) => 18 + d.riskScore * 1.5,
        sizeMinPixels: 12,
        sizeMaxPixels: 40,
        sizeUnits: 'pixels',
        billboard: true,
        pickable: true,
        onClick: (info) => {
          if (info.object) {
            setSelectedEntityId(info.object.id);
            setSelectedEntity({
              id: info.object.id,
              type: info.object.type,
              name: info.object.name,
              properties: {},
              confidence: info.object.confidence,
              sourceInt: info.object.sourceInt,
              riskScore: info.object.riskScore,
              firstSeen: '',
              lastSeen: '',
            });
          }
        },
        updateTriggers: {
          getSize: [entities],
        },
      }),
    );
  }

  if (visibleLayers.has('connections') && entities.length > 1) {
    const arcs = entities.slice(0, 30).flatMap((source, i) =>
      entities.slice(i + 1, i + 2).map((target) => ({
        source: [source.position.longitude, source.position.latitude] as [number, number],
        target: [target.position.longitude, target.position.latitude] as [number, number],
        sourceColor: getEntityColor(source.type),
        targetColor: getEntityColor(target.type),
      })),
    );

    layers.push(
      new ArcLayer({
        id: 'globe-arcs',
        data: arcs,
        getSourcePosition: (d) => d.source,
        getTargetPosition: (d) => d.target,
        getSourceColor: (d) => [...d.sourceColor, 120] as [number, number, number, number],
        getTargetColor: (d) => [...d.targetColor, 120] as [number, number, number, number],
        getWidth: 2,
        greatCircle: true,
      }),
    );
  }

  // Active Tracks (Flights/Vessels) on Globe
  const trackEntries = Array.from(activeTracks.entries());
  const flightTracks = trackEntries.filter(([id]) => id.startsWith('aircraft-') || id.startsWith('flight-'));
  const vesselTracks = trackEntries.filter(([id]) => id.startsWith('vessel-'));

  if (visibleLayers.has('flights') && flightTracks.length > 0) {
    layers.push(
      new PathLayer({
        id: 'globe-flight-paths',
        data: flightTracks.map(([id, points]) => ({
          path: points.map((p) => [p.position.longitude, p.position.latitude, p.position.altitude || 0]),
          id,
        })),
        getPath: (d) => d.path,
        getColor: [0, 229, 255, 40],
        getWidth: 2,
        widthMinPixels: 1,
        widthMaxPixels: 6,
        billboard: true,
      }),
      new TripsLayer({
        id: 'globe-flight-trips',
        data: flightTracks.map(([id, points]) => {
          const totalPoints = points.length;
          const path = points.map((p) => [p.position.longitude, p.position.latitude, p.position.altitude || 0]);
          const timestamps = points.map((_, i) => (i / Math.max(1, totalPoints - 1)) * 1000);
          return { id, path, timestamps };
        }),
        getPath: (d) => d.path,
        getTimestamps: (d) => d.timestamps,
        getColor: [0, 255, 200],
        opacity: 0.8,
        widthMinPixels: 4,
        trailLength: 300,
        currentTime: playbackTime,
        billboard: true,
      })
    );
  }

  if (visibleLayers.has('vessels') && vesselTracks.length > 0) {
    layers.push(
      new PathLayer({
        id: 'globe-vessel-paths',
        data: vesselTracks.map(([id, points]) => ({
          path: points.map((p) => [p.position.longitude, p.position.latitude]),
          id,
        })),
        getPath: (d) => d.path,
        getColor: [32, 178, 170, 40],
        getWidth: 1.5,
        widthMinPixels: 1,
        widthMaxPixels: 6,
        billboard: true,
      }),
      new TripsLayer({
        id: 'globe-vessel-trips',
        data: vesselTracks.map(([id, points]) => {
          const totalPoints = points.length;
          const path = points.map((p) => [p.position.longitude, p.position.latitude]);
          const timestamps = points.map((_, i) => (i / Math.max(1, totalPoints - 1)) * 1000);
          return { id, path, timestamps };
        }),
        getPath: (d) => d.path,
        getTimestamps: (d) => d.timestamps,
        getColor: [32, 220, 200],
        opacity: 0.8,
        widthMinPixels: 3,
        trailLength: 200,
        currentTime: playbackTime,
        billboard: true,
      })
    );
  }

  // Head markers on globe — icon at current interpolated position
  const allGlobeTracks = [...flightTracks, ...vesselTracks];
  if (allGlobeTracks.length > 0) {
    const headData = allGlobeTracks
      .map(([id, points]) => {
        const progress = playbackTime / Math.max(1, useMapStore.getState().playbackMaxTime);
        const pos = interpolateTrackPosition(points, progress);
        if (!pos) return null;
        const isFlight = id.startsWith('aircraft-') || id.startsWith('flight-');
        const entityType = isFlight ? 'Aircraft' : 'Vessel';
        const idx = Math.min(Math.floor(progress * (points.length - 1)), points.length - 1);
        const heading = points[idx]?.heading || 0;
        const act = entityActivities.get(id);
        return {
          id,
          position: [pos.longitude, pos.latitude, pos.altitude || 0] as [number, number, number],
          color: isFlight ? [0, 255, 220, 255] as [number, number, number, number] : [32, 220, 200, 255] as [number, number, number, number],
          label: id.replace(/^(aircraft-|flight-|vessel-)/, '').substring(0, 8),
          entityType,
          heading,
          activity: act?.activity,
        };
      })
      .filter(Boolean) as Array<{ id: string; position: [number, number, number]; color: [number, number, number, number]; label: string; entityType: string; heading: number; activity?: string }>;

    // Glow ring
    layers.push(
      new ScatterplotLayer({
        id: 'globe-head-glow',
        data: headData,
        getPosition: (d) => d.position,
        getRadius: 100000,
        getFillColor: (d) => [d.color[0], d.color[1], d.color[2], 60] as [number, number, number, number],
        radiusMinPixels: 10,
        radiusMaxPixels: 24,
        updateTriggers: { getPosition: [playbackTime] },
      }),
    );

    // Icon at track head
    layers.push(
      new IconLayer({
        id: 'globe-head-icon',
        data: headData,
        iconAtlas: iconAtlas,
        iconMapping: iconMapping,
        getIcon: (d) => d.entityType,
        getPosition: (d) => d.position,
        getSize: 26,
        sizeMinPixels: 18,
        sizeMaxPixels: 44,
        sizeUnits: 'pixels',
        getAngle: (d) => d.heading ? 360 - d.heading : 0,
        billboard: true,
        updateTriggers: { getPosition: [playbackTime], getAngle: [playbackTime] },
      }),
    );

    // Drop-lines for 3D aerial tracks
    const aerialHeads = headData.filter(d => d.position[2] > 0);
    if (aerialHeads.length > 0) {
      layers.push(
        new LineLayer({
          id: 'globe-track-drop-lines',
          data: aerialHeads,
          getSourcePosition: (d: any) => d.position,
          getTargetPosition: (d: any) => [d.position[0], d.position[1], 0],
          getColor: (d: any) => [d.color[0], d.color[1], d.color[2], 100],
          getWidth: 1,
          widthMinPixels: 1,
        }),
      );
    }

    // Label
    layers.push(
      new TextLayer({
        id: 'globe-head-label',
        data: headData,
        getPosition: (d) => d.position,
        getText: (d) => d.activity ? `${d.label}\n${d.activity}` : d.label,
        getColor: [255, 255, 255, 200],
        getSize: 11,
        getPixelOffset: [0, -18],
        fontFamily: 'monospace',
        fontWeight: 700,
        outlineWidth: 2,
        outlineColor: [0, 0, 0, 200],
        billboard: true,
        updateTriggers: { getPosition: [playbackTime], getText: [playbackTime, entityActivities] },
      }),
    );
  }

  // GPS accuracy circle for followed entity
  if (followEntityId && followMode !== 'off') {
    const followTrack = activeTracks.get(followEntityId);
    if (followTrack && followTrack.length > 0) {
      const latestPt = followTrack[followTrack.length - 1];
      const accuracy = latestPt.position.accuracy;
      if (accuracy && accuracy > 0) {
        layers.push(
          new ScatterplotLayer({
            id: 'gps-accuracy-circle',
            data: [{
              position: [latestPt.position.longitude, latestPt.position.latitude] as [number, number],
              accuracy,
            }],
            getPosition: (d: any) => d.position,
            getRadius: (d: any) => d.accuracy,
            getFillColor: [0, 212, 255, 20],
            getLineColor: [0, 212, 255, 80],
            stroked: true,
            getLineWidth: 2,
            lineWidthMinPixels: 1,
            radiusUnits: 'meters',
            filled: true,
            pickable: false,
          }),
        );
      }
    }
  }

  if (!webglOk || deckError) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-nexus-bg">
        <div className="text-center max-w-sm">
          <div className="text-nexus-amber text-lg font-heading mb-2">
            {deckError ? 'Globe Rendering Error' : 'WebGL Unavailable'}
          </div>
          <p className="text-nexus-text-secondary text-sm">
            {deckError
              ? 'The globe renderer encountered an error. Try reloading or check your GPU drivers.'
              : 'Globe rendering requires WebGL support. Please check your GPU drivers or enable hardware acceleration.'}
          </p>
          {deckError && (
            <button
              onClick={() => setDeckError(false)}
              className="mt-3 px-4 py-1.5 text-xs font-mono bg-nexus-cyan/20 text-nexus-cyan rounded border border-nexus-cyan/30 hover:bg-nexus-cyan/30 transition-colors"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full" style={{ background: '#0a0a1a' }}>
      <DeckGL
        views={globeView}
        viewState={viewState}
        onViewStateChange={({ viewState: vs, interactionState }) => {
          // Disengage follow mode on manual interaction
          if (
            followEntityId &&
            (interactionState?.isPanning || interactionState?.isRotating || interactionState?.isZooming)
          ) {
            setFollowEntity(null);
            setFollowMode('off');
          }
          setViewState(vs as unknown as { longitude: number; latitude: number; zoom: number; bearing: number; pitch: number });
        }}
        controller={true}
        layers={layers}
        getCursor={({ isHovering }) => (isHovering ? 'pointer' : 'grab')}
        onError={(error) => {
          console.warn('[DeckGL] Globe rendering error caught:', error);
          setDeckError(true);
        }}
      >
        {zoomProgress > 0 && (
          <MapGL
            mapStyle={mapStyle as any}
            attributionControl={false}
            style={{ opacity: zoomProgress }}
          />
        )}
      </DeckGL>

      <div className="absolute bottom-3 left-3 flex items-center gap-2">
        <div className="bg-nexus-card/90 border border-nexus-border rounded px-2 py-1 text-[10px] font-mono text-nexus-text-secondary">
          {entities.length} entities
        </div>
        <div className={`px-1.5 py-0.5 rounded text-[9px] font-mono border ${viewModeLabel === '3D'
          ? 'text-nexus-cyan border-nexus-cyan/40 bg-nexus-cyan/10'
          : viewModeLabel === 'STREET'
            ? 'text-nexus-green border-nexus-green/40 bg-nexus-green/10'
            : 'text-nexus-text-secondary border-nexus-border'
          }`}>
          {viewModeLabel}
        </div>
        {terrainActive && (
          <div className="px-1.5 py-0.5 rounded text-[9px] font-mono text-amber-400 border border-amber-400/40 bg-amber-400/10">
            TERRAIN
          </div>
        )}
        {followEntityId && followMode !== 'off' && (
          <div className="px-1.5 py-0.5 rounded text-[9px] font-mono text-nexus-cyan border border-nexus-cyan/40 bg-nexus-cyan/10 animate-pulse">
            FOLLOWING
          </div>
        )}
      </div>
    </div>
  );
}
