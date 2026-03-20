import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import MapGL, { NavigationControl, type ViewStateChangeEvent } from 'react-map-gl/maplibre';
import { DeckGL } from '@deck.gl/react';
import { ScatterplotLayer, ArcLayer, PathLayer, TextLayer, IconLayer, LineLayer } from '@deck.gl/layers';
import { TripsLayer } from '@deck.gl/geo-layers';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useMapStore } from '@/stores/useMapStore';
import { useEntityStore } from '@/stores/useEntityStore';
import { map as mapApi } from '@/services/api';
import { LayerControl } from './controls/LayerControl';
import { EntityPopup } from './popups/EntityPopup';
import { createSatelliteImageryLayer } from './layers/SatelliteImageryLayer';
import { createOsmFeatureLayer } from './layers/OsmFeatureLayer';
import { createHeatmapLayer } from './layers/HeatmapLayer';
import { createGeofenceLayer } from './layers/GeofenceLayer';
import { createCoordinateGridLayer } from './layers/CoordinateGridLayer';
import { useHeatmapData } from '@/hooks/useHeatmap';
import { interpolateTrackPosition } from '@/utils/geoUtils';
import { createEntityIconAtlas, getEntityColor, getEntityIcon } from './icons/entityIcons';
import { createNexusMapStyle } from './styles/nexusDarkStyle';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';
import { createCommercialFlightLayer, createMilitaryFlightLayer, createTrackedFlightLayer, createUAVLayer, createFlightTrailLayer, createGPSJammingLayer, createHoldingPatternLayer } from '@/components/map/layers/FlightLayers';
import { createEarthquakeLayer, createFireLayer, createWeatherRadarLayer } from '@/components/map/layers/EarthObservationLayers';
import { createSatelliteLayer } from '@/components/map/layers/SatelliteLayers';
import { createGDELTLayer, createInternetOutageLayer, createAirportLayer, createMilitaryBaseLayer, createDatacenterLayer, createKiwiSDRLayer } from '@/components/map/layers/InfrastructureLayers';
import { FlightDetailPopup } from '@/components/map/popups/FlightDetailPopup';
import type { LiveFlight, MilitaryFlight } from '@/types/livefeed';

function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

// Label visibility thresholds
const NAME_LABEL_ZOOM = 6;
const ACTIVITY_LABEL_ZOOM = 8;

interface MapEntityData {
  id: string;
  type: string;
  name: string;
  position: { latitude: number; longitude: number };
  confidence: number;
  sourceInt: string;
  riskScore: number;
  activity?: string;
  activityType?: string;
}

export function MapView() {
  const {
    viewState, setViewState, visibleLayers, setSelectedEntityId, selectedEntityId,
    activeTracks, geofences, geofenceEditMode, geofenceVertices,
    playbackTime, addGeofenceVertex, entityActivities,
  } = useMapStore();
  const { setSelectedEntity } = useEntityStore();

  // Entity cache — retains previous results to prevent flickering on zoom
  const entityCacheRef = useRef<Map<string, MapEntityData>>(new Map());
  const [entities, setEntities] = useState<MapEntityData[]>([]);
  const [hoveredEntity, setHoveredEntity] = useState<MapEntityData | null>(null);
  const [popupCoords, setPopupCoords] = useState<{ x: number; y: number } | null>(null);
  const [selectedFlight, setSelectedFlight] = useState<LiveFlight | MilitaryFlight | null>(null);

  const { flights, militaryFlights, trackedFlights, uavs, earthquakes, fires, gpsJamming, weatherRadar, satellites, gdelt, internetOutages, airports, militaryBases, kiwisdr, datacenters, powerPlants } = useLiveFeedStore() as any;
  const [webglOk] = useState(() => isWebGLAvailable());
  const [deckError, setDeckError] = useState(false);

  // Icon atlas — memoized once (cast to any for deck.gl compatibility)
  const { atlas: iconAtlas, mapping: iconMapping } = useMemo(() => {
    const result = createEntityIconAtlas();
    return { atlas: result.atlas as any, mapping: result.mapping };
  }, []);

  // Custom map style — memoized once
  const mapStyle = useMemo(() => createNexusMapStyle(), []);

  // Fetch entities with expanded bbox + cache merging
  const fetchEntities = useCallback(async () => {
    try {
      const zoom = viewState.zoom;
      const range = 180 / Math.pow(2, zoom);
      const padding = range * 0.3; // 30% padding for prefetch
      const bbox = {
        west: viewState.longitude - range - padding,
        south: viewState.latitude - range / 2 - padding,
        east: viewState.longitude + range + padding,
        north: viewState.latitude + range / 2 + padding,
      };

      // Always fetch individual entities at every zoom level
      const data = (await mapApi.getEntities(bbox)) as MapEntityData[];
      const cache = entityCacheRef.current;
      for (const e of data) cache.set(e.id, e);

      // Render entities within extended viewport (current + 20% margin)
      const renderRange = range * 1.2;
      const visible = Array.from(cache.values()).filter((e) => {
        const dlng = Math.abs(e.position.longitude - viewState.longitude);
        const dlat = Math.abs(e.position.latitude - viewState.latitude);
        return dlng <= renderRange && dlat <= renderRange / 2;
      });
      setEntities(visible);
    } catch (err) {
      console.error('[Map] Entity fetch failed:', err);
    }
  }, [viewState.longitude, viewState.latitude, viewState.zoom]);

  useEffect(() => {
    const timer = setTimeout(fetchEntities, 300);
    return () => clearTimeout(timer);
  }, [fetchEntities]);

  const onViewStateChange = useCallback(
    (evt: ViewStateChangeEvent) => {
      setViewState(evt.viewState);
    },
    [setViewState],
  );

  // Deck.gl layers
  const layers = [];

  // ─── Entity icon layers (all zoom levels) ────────────
  if (visibleLayers.has('entities') && entities.length > 0) {
    const zoom = viewState.zoom;

    // Glow ring behind each icon — smaller at low zoom
    layers.push(
      new ScatterplotLayer<MapEntityData>({
        id: 'entity-glow',
        data: entities,
        getPosition: (d) => [d.position.longitude, d.position.latitude],
        getRadius: 6000,
        getFillColor: (d) => {
          const c = getEntityColor(d.type);
          const alpha = Math.round(d.confidence * 80 + 20);
          return [...c, alpha] as [number, number, number, number];
        },
        radiusMinPixels: zoom < 4 ? 3 : zoom < 8 ? 5 : 8,
        radiusMaxPixels: 20,
        pickable: false,
      }),
    );

    // Icon layer — entity type SVG (adaptive sizing for low zoom)
    layers.push(
      new IconLayer<MapEntityData>({
        id: 'entity-icon',
        data: entities,
        iconAtlas: iconAtlas,
        iconMapping: iconMapping,
        getIcon: (d) => (iconMapping[d.type] ? d.type : '_default'),
        getPosition: (d) => [d.position.longitude, d.position.latitude],
        getSize: (d) => 20 + d.riskScore * 2,
        sizeMinPixels: zoom < 4 ? 6 : zoom < 8 ? 10 : 16,
        sizeMaxPixels: 48,
        sizeUnits: 'pixels',
        getAngle: (d) => {
          const def = getEntityIcon(d.type);
          if (!def.rotatable) return 0;
          const track = activeTracks.get(d.id);
          if (track && track.length > 0) {
            const last = track[track.length - 1];
            return last.heading ? 360 - last.heading : 0;
          }
          return 0;
        },
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
        onHover: (info) => {
          if (info.object) {
            setHoveredEntity(info.object);
            setPopupCoords({ x: info.x, y: info.y });
          } else {
            setHoveredEntity(null);
            setPopupCoords(null);
          }
        },
        updateTriggers: {
          getAngle: [activeTracks],
          getSize: [selectedEntityId],
          sizeMinPixels: [zoom],
        },
      }),
    );

    // Name labels (zoom >= NAME_LABEL_ZOOM)
    if (zoom >= NAME_LABEL_ZOOM) {
      layers.push(
        new TextLayer<MapEntityData>({
          id: 'entity-name-label',
          data: entities,
          getPosition: (d) => [d.position.longitude, d.position.latitude],
          getText: (d) => d.name.length > 16 ? d.name.substring(0, 15) + '\u2026' : d.name,
          getColor: (d) => {
            const c = getEntityColor(d.type);
            return [...c, 200] as [number, number, number, number];
          },
          getSize: zoom < 8 ? 8 : 10,
          getPixelOffset: [0, zoom < 8 ? 12 : 20],
          fontFamily: 'monospace',
          fontWeight: 600,
          outlineWidth: 2,
          outlineColor: [0, 0, 0, 220],
          billboard: true,
          updateTriggers: { getText: [entities] },
        }),
      );
    }

    // Activity labels (zoom >= ACTIVITY_LABEL_ZOOM, for entities with activity)
    if (zoom >= ACTIVITY_LABEL_ZOOM && entityActivities.size > 0) {
      const entitiesWithActivity = entities.filter((e) => entityActivities.has(e.id));
      if (entitiesWithActivity.length > 0) {
        const ACTIVITY_COLORS: Record<string, [number, number, number, number]> = {
          alert: [255, 70, 70, 220],
          scanning: [255, 184, 0, 200],
          moving: [0, 255, 136, 200],
          communicating: [0, 212, 255, 200],
          idle: [140, 140, 140, 160],
        };

        layers.push(
          new TextLayer({
            id: 'entity-activity-label',
            data: entitiesWithActivity,
            getPosition: (d: MapEntityData) => [d.position.longitude, d.position.latitude],
            getText: (d: MapEntityData) => {
              const act = entityActivities.get(d.id);
              return act?.activity || '';
            },
            getColor: (d: MapEntityData) => {
              const act = entityActivities.get(d.id);
              return ACTIVITY_COLORS[act?.activityType || 'idle'] || ACTIVITY_COLORS.idle;
            },
            getSize: 9,
            getPixelOffset: [0, 32],
            fontFamily: 'monospace',
            fontWeight: 400,
            fontSettings: { sdf: false },
            outlineWidth: 1.5,
            outlineColor: [0, 0, 0, 200],
            billboard: true,
            updateTriggers: { getText: [entityActivities], getColor: [entityActivities] },
          }),
        );

        // Pulsing alert dot for entities with alert activity
        const alertEntities = entitiesWithActivity.filter(
          (e) => entityActivities.get(e.id)?.activityType === 'alert',
        );
        if (alertEntities.length > 0) {
          layers.push(
            new ScatterplotLayer({
              id: 'entity-alert-pulse',
              data: alertEntities,
              getPosition: (d: MapEntityData) => [d.position.longitude, d.position.latitude],
              getRadius: 3000,
              getFillColor: [255, 50, 50, 160],
              radiusMinPixels: 12,
              radiusMaxPixels: 24,
              stroked: true,
              getLineColor: [255, 50, 50, 80],
              getLineWidth: 2,
              lineWidthMinPixels: 1,
            }),
          );
        }
      }
    }
  }

  // Heatmap layer
  const bbox = useMemo(() => {
    const zoom = viewState.zoom;
    const range = 180 / Math.pow(2, zoom);
    return {
      west: viewState.longitude - range,
      south: viewState.latitude - range / 2,
      east: viewState.longitude + range,
      north: viewState.latitude + range / 2,
    };
  }, [viewState.longitude, viewState.latitude, viewState.zoom]);

  const { data: heatmapRaw } = useHeatmapData(visibleLayers.has('heatmap') ? bbox : null);
  const heatmapPoints = (heatmapRaw as Array<{ latitude: number; longitude: number; weight: number }> || []).map(
    (p) => ({ position: [p.longitude, p.latitude] as [number, number], weight: p.weight || 1 }),
  );
  layers.push(createHeatmapLayer(heatmapPoints, visibleLayers.has('heatmap')));

  // GEOINT layers — fetch satellite imagery and OSM features for viewport
  const [satData, setSatData] = useState<any[]>([]);
  const [osmData, setOsmData] = useState<any>(null);
  const [satPopup, setSatPopup] = useState<{ data: any; x: number; y: number } | null>(null);

  useEffect(() => {
    if (!visibleLayers.has('satellite') || viewState.zoom < 8) { setSatData([]); return; }
    const ctrl = new AbortController();
    const fetchSat = async () => {
      try {
        const { geoint } = await import('@/services/api');
        const results = await geoint.searchSatellite(bbox);
        setSatData(results as any[]);
      } catch { /* API not available */ }
    };
    const t = setTimeout(fetchSat, 500);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [visibleLayers.has('satellite'), viewState.zoom, bbox.west, bbox.south]);

  useEffect(() => {
    if (!visibleLayers.has('osm') || viewState.zoom < 12) { setOsmData(null); return; }
    const fetchOsm = async () => {
      try {
        const { geoint } = await import('@/services/api');
        const features = await geoint.getOsmFeatures(bbox);
        setOsmData({ type: 'FeatureCollection', features: features || [] });
      } catch { /* API not available */ }
    };
    const t = setTimeout(fetchOsm, 500);
    return () => clearTimeout(t);
  }, [visibleLayers.has('osm'), viewState.zoom, bbox.west, bbox.south]);

  layers.push(createSatelliteImageryLayer(satData, visibleLayers.has('satellite'), (info) => {
    if (info.object) setSatPopup({ data: info.object, x: 0, y: 0 });
  }));
  layers.push(createOsmFeatureLayer(osmData, visibleLayers.has('osm')));

  // Geofence layer
  layers.push(createGeofenceLayer(geofences, visibleLayers.has('geofence'), geofenceEditMode ? geofences[geofences.length - 1]?.id || null : null));

  // Coordinate Grid layer
  const gridLayer = createCoordinateGridLayer(true, viewState.zoom, viewState);
  if (gridLayer) layers.push(gridLayer);

  // Flight & Vessel track layers
  const trackEntries = Array.from(activeTracks.entries());
  const flightTracks = trackEntries.filter(([id]) => id.startsWith('aircraft-') || id.startsWith('flight-'));
  const vesselTracks = trackEntries.filter(([id]) => id.startsWith('vessel-'));

  if (visibleLayers.has('flights') && flightTracks.length > 0) {
    layers.push(
      new PathLayer({
        id: 'flight-paths-bg',
        data: flightTracks.map(([id, points]) => ({
          path: points.map((p) => [p.position.longitude, p.position.latitude, p.position.altitude || 0]),
          id,
        })),
        getPath: (d) => d.path,
        getColor: [0, 229, 255, 40],
        getWidth: 1.5,
        widthMinPixels: 1,
        widthMaxPixels: 6,
      }),
    );

    layers.push(
      new TripsLayer({
        id: 'flight-trips',
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
        widthMinPixels: 3,
        widthMaxPixels: 8,
        rounded: true,
        trailLength: 300,
        currentTime: playbackTime,
      }),
    );
  }

  if (visibleLayers.has('vessels') && vesselTracks.length > 0) {
    layers.push(
      new PathLayer({
        id: 'vessel-paths-bg',
        data: vesselTracks.map(([id, points]) => ({
          path: points.map((p) => [p.position.longitude, p.position.latitude]),
          id,
        })),
        getPath: (d) => d.path,
        getColor: [32, 178, 170, 40],
        getWidth: 1.5,
        widthMinPixels: 1,
        widthMaxPixels: 6,
      }),
    );

    layers.push(
      new TripsLayer({
        id: 'vessel-trips',
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
        widthMaxPixels: 8,
        trailLength: 200,
        currentTime: playbackTime,
      }),
    );
  }

  // Head markers — icon at each track's current interpolated position
  const allTracks = [...flightTracks, ...vesselTracks];
  if (allTracks.length > 0) {
    const headData = allTracks
      .map(([id, points]) => {
        const progress = playbackTime / Math.max(1, useMapStore.getState().playbackMaxTime);
        const pos = interpolateTrackPosition(points, progress);
        if (!pos) return null;
        const isFlight = id.startsWith('aircraft-') || id.startsWith('flight-');
        const entityType = isFlight ? 'Aircraft' : 'Vessel';
        // Get heading from nearest track point
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

    // Outer glow ring
    layers.push(
      new ScatterplotLayer({
        id: 'track-head-glow',
        data: headData,
        getPosition: (d) => d.position,
        getRadius: 12,
        getFillColor: (d) => [d.color[0], d.color[1], d.color[2], 60] as [number, number, number, number],
        radiusMinPixels: 10,
        radiusMaxPixels: 24,
        updateTriggers: { getPosition: [playbackTime] },
      }),
    );

    // Icon at track head (Aircraft/Vessel SVG with heading rotation)
    layers.push(
      new IconLayer({
        id: 'track-head-icon',
        data: headData,
        iconAtlas: iconAtlas,
        iconMapping: iconMapping,
        getIcon: (d) => d.entityType,
        getPosition: (d) => d.position,
        getSize: 28,
        sizeMinPixels: 20,
        sizeMaxPixels: 48,
        sizeUnits: 'pixels',
        getAngle: (d) => d.heading ? 360 - d.heading : 0,
        billboard: false,
        updateTriggers: { getPosition: [playbackTime], getAngle: [playbackTime] },
      }),
    );

    // Drop-lines for 3D aerial tracks
    const aerialHeads = headData.filter(d => d.position[2] > 0);
    if (aerialHeads.length > 0) {
      layers.push(
        new LineLayer({
          id: 'track-drop-lines',
          data: aerialHeads,
          getSourcePosition: (d) => d.position,
          getTargetPosition: (d) => [d.position[0], d.position[1], 0],
          getColor: (d) => [d.color[0], d.color[1], d.color[2], 150],
          getWidth: 1,
          widthMinPixels: 1,
        }),
      );

      // Ground target reticle where the drop line hits
      layers.push(
        new ScatterplotLayer({
          id: 'track-drop-reticles',
          data: aerialHeads,
          getPosition: (d) => [d.position[0], d.position[1], 0],
          getRadius: 15,
          getFillColor: [0, 0, 0, 0],
          stroked: true,
          getLineColor: (d) => [d.color[0], d.color[1], d.color[2], 200],
          getLineWidth: 2,
          radiusMinPixels: 4,
          radiusMaxPixels: 10,
        }),
      );
    }

    // Label (with activity text if available)
    layers.push(
      new TextLayer({
        id: 'track-head-label',
        data: headData,
        getPosition: (d) => d.position,
        getText: (d) => d.activity ? `${d.label}\n${d.activity}` : d.label,
        getColor: [255, 255, 255, 200],
        getSize: 11,
        getPixelOffset: [0, -22],
        fontFamily: 'monospace',
        fontWeight: 700,
        outlineWidth: 2,
        outlineColor: [0, 0, 0, 200],
        updateTriggers: { getPosition: [playbackTime], getText: [playbackTime, entityActivities] },
      }),
    );
  }

  // Selected entity trail highlight
  if (selectedEntityId) {
    const selectedTrack = activeTracks.get(selectedEntityId);
    if (selectedTrack && selectedTrack.length > 1) {
      layers.push(
        new PathLayer({
          id: 'selected-entity-trail',
          data: [{
            path: selectedTrack.map((p) => [p.position.longitude, p.position.latitude, p.position.altitude || 0]),
          }],
          getPath: (d) => d.path,
          getColor: [255, 215, 0, 180],
          getWidth: 3,
          widthMinPixels: 2,
          getDashArray: [8, 4],
          dashJustified: true,
          extensions: [],
        }),
      );
    }
  }

  // Geofence vertex drawing — when in edit mode, show placed vertices + progress outline
  if (geofenceEditMode && geofenceVertices.length > 0) {
    layers.push(
      new ScatterplotLayer({
        id: 'geofence-vertices',
        data: geofenceVertices.map((v, i) => ({ position: v, index: i })),
        getPosition: (d) => d.position,
        getRadius: 6,
        getFillColor: [255, 184, 0, 220],
        radiusMinPixels: 5,
        radiusMaxPixels: 10,
        stroked: true,
        getLineColor: [255, 255, 255, 200],
        getLineWidth: 2,
        lineWidthMinPixels: 1,
      }),
    );

    if (geofenceVertices.length >= 2) {
      const outlinePath = [...geofenceVertices];
      if (geofenceVertices.length >= 3) {
        outlinePath.push(geofenceVertices[0]);
      }
      layers.push(
        new PathLayer({
          id: 'geofence-outline-progress',
          data: [{ path: outlinePath }],
          getPath: (d) => d.path,
          getColor: [255, 184, 0, 150],
          getWidth: 2,
          widthMinPixels: 1,
          getDashArray: [6, 3],
          dashJustified: true,
        }),
      );
    }
  }

  // ─── Live Feed layers ────────────
  if (visibleLayers.has('liveFlights') && flights.length > 0) {
    layers.push(createCommercialFlightLayer(flights, (info) => {
      if (info.object) setSelectedFlight(info.object as LiveFlight);
    }));
    layers.push(createFlightTrailLayer(flights));
    const holdingFlights = flights.filter((f) => f.holding);
    if (holdingFlights.length > 0) layers.push(createHoldingPatternLayer(holdingFlights));
  }

  if (visibleLayers.has('military') && militaryFlights.length > 0) {
    layers.push(createMilitaryFlightLayer(militaryFlights, (info) => {
      if (info.object) setSelectedFlight(info.object as MilitaryFlight);
    }));
  }

  if (visibleLayers.has('trackedAircraft') && trackedFlights.length > 0) {
    layers.push(createTrackedFlightLayer(trackedFlights, (info) => {
      if (info.object) setSelectedFlight(info.object as LiveFlight);
    }));
  }

  if (visibleLayers.has('uavs') && uavs.length > 0) {
    layers.push(createUAVLayer(uavs));
  }

  if (visibleLayers.has('earthquakes') && earthquakes.length > 0) {
    layers.push(createEarthquakeLayer(earthquakes));
  }

  if (visibleLayers.has('activeFires') && fires.length > 0) {
    layers.push(createFireLayer(fires));
  }

  if (visibleLayers.has('weatherRadar') && weatherRadar) {
    layers.push(createWeatherRadarLayer(weatherRadar));
  }

  if (visibleLayers.has('gpsJamming') && gpsJamming.length > 0) {
    layers.push(createGPSJammingLayer(gpsJamming));
  }

  if (visibleLayers.has('satellites') && satellites?.length > 0) {
    layers.push(createSatelliteLayer(satellites));
  }

  if (visibleLayers.has('gdelt') && gdelt?.length > 0) {
    layers.push(createGDELTLayer(gdelt));
  }

  if (visibleLayers.has('internetOutages') && internetOutages?.length > 0) {
    layers.push(createInternetOutageLayer(internetOutages));
  }

  if (visibleLayers.has('airports') && airports?.length > 0) {
    layers.push(createAirportLayer(airports));
  }

  if (visibleLayers.has('militaryBases') && militaryBases?.length > 0) {
    layers.push(createMilitaryBaseLayer(militaryBases));
  }

  if (visibleLayers.has('datacenters') && datacenters?.length > 0) {
    layers.push(createDatacenterLayer(datacenters));
  }

  if (visibleLayers.has('kiwisdr') && kiwisdr?.length > 0) {
    layers.push(createKiwiSDRLayer(kiwisdr));
  }

  if (visibleLayers.has('connections') && entities.length > 1) {
    const arcs = entities.slice(0, 50).flatMap((source, i) =>
      entities.slice(i + 1, i + 3).map((target) => ({
        source: [source.position.longitude, source.position.latitude] as [number, number],
        target: [target.position.longitude, target.position.latitude] as [number, number],
        sourceColor: getEntityColor(source.type),
        targetColor: getEntityColor(target.type),
      })),
    );

    layers.push(
      new ArcLayer({
        id: 'connection-layer',
        data: arcs,
        getSourcePosition: (d) => d.source,
        getTargetPosition: (d) => d.target,
        getSourceColor: (d) => [...d.sourceColor, 150] as [number, number, number, number],
        getTargetColor: (d) => [...d.targetColor, 150] as [number, number, number, number],
        getWidth: 1.5,
        tilt: 15,
      }),
    );
  }

  if (!webglOk || deckError) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-nexus-bg">
        <div className="text-center max-w-sm">
          <div className="text-nexus-amber text-lg font-heading mb-2">
            {deckError ? 'Map Rendering Error' : 'WebGL Unavailable'}
          </div>
          <p className="text-nexus-text-secondary text-sm">
            {deckError
              ? 'The map renderer encountered an error. Try reloading or check your GPU drivers.'
              : 'Map rendering requires WebGL support. Please check your GPU drivers or enable hardware acceleration.'}
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

  const zoomLevel = viewState.zoom;
  const entityCount = entities.length;

  return (
    <div className="relative w-full h-full">
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState }) => onViewStateChange({ viewState } as any)}
        controller={true as any}
        layers={layers}
        getCursor={({ isHovering }) => (geofenceEditMode ? 'crosshair' : isHovering ? 'pointer' : 'grab')}
        onClick={(info) => {
          if (geofenceEditMode && info.coordinate) {
            addGeofenceVertex([info.coordinate[0], info.coordinate[1]]);
          }
        }}
        onError={(error) => {
          console.warn('[DeckGL] Rendering error caught:', error);
          setDeckError(true);
        }}
      >
        <MapGL
          mapStyle={mapStyle as any}
          attributionControl={true}
        >
          <NavigationControl position="bottom-right" />
        </MapGL>
      </DeckGL>

      {/* Layer control */}
      <div className="absolute top-3 right-3">
        <LayerControl />
      </div>

      {/* Entity popup on hover */}
      {hoveredEntity && popupCoords && (
        <div
          className="absolute pointer-events-none z-10"
          style={{ left: popupCoords.x + 10, top: popupCoords.y - 10 }}
        >
          <EntityPopup entity={hoveredEntity} />
        </div>
      )}

      {/* Flight detail popup */}
      {selectedFlight && (
        <FlightDetailPopup flight={selectedFlight} onClose={() => setSelectedFlight(null)} />
      )}

      {/* Satellite detail popup */}
      {satPopup && (
        <div className="absolute top-16 right-16 z-20 bg-nexus-card/95 backdrop-blur-sm border border-nexus-cyan/30 rounded-lg p-3 w-64 shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-nexus-cyan uppercase tracking-wider">Satellite Pass</span>
            <button onClick={() => setSatPopup(null)} className="text-nexus-text-secondary hover:text-nexus-text text-xs">X</button>
          </div>
          <div className="space-y-1 text-[10px] font-mono">
            <p className="text-nexus-text">Name: <span className="text-nexus-cyan">{satPopup.data.name || 'Unknown'}</span></p>
            <p className="text-nexus-text-secondary">Date: {satPopup.data.date || 'N/A'}</p>
            <p className="text-nexus-text-secondary">Cloud: {satPopup.data.cloud_cover ?? 'N/A'}%</p>
            <p className="text-nexus-text-secondary">BBox: {satPopup.data.bbox?.join(', ')}</p>
          </div>
        </div>
      )}

      {/* Zoom level + entity count + mode indicator */}
      <div className="absolute bottom-3 left-3 bg-nexus-card/90 border border-nexus-border rounded px-2 py-1 text-[10px] font-mono text-nexus-text-secondary flex items-center gap-2">
        <span>Z{zoomLevel.toFixed(1)}</span>
        <span className="text-nexus-border">|</span>
        <span>{entityCount} entities</span>
        {zoomLevel >= 15 && <span className="text-nexus-cyan">STREET</span>}
        {zoomLevel >= 16 && <span className="text-amber-400">3D</span>}
      </div>
    </div>
  );
}
