import { create } from 'zustand';
import type { MapViewState, MapEntity, TrackPoint } from '@/types';
import type { Geofence } from '@/components/map/layers/GeofenceLayer';
import { TrackAnimator } from '@/components/map/layers/TrackAnimator';

type PlaybackState = 'stopped' | 'playing' | 'paused';
type FollowMode = 'off' | 'center' | 'track';

// Module-level animator (outside Zustand to avoid storing class instances)
let _animator: TrackAnimator | null = null;

export interface EntityActivity {
  activity: string;
  activityType: string;
  timestamp: string;
}

interface MapState {
  viewState: MapViewState;
  visibleLayers: Set<string>;
  selectedEntityId: string | null;
  activeTracks: Map<string, TrackPoint[]>;
  mapEntities: MapEntity[];
  entityActivities: Map<string, EntityActivity>;
  is3D: boolean;
  playbackState: PlaybackState;
  playbackTime: number;
  playbackMaxTime: number;
  playbackSpeed: number;
  liveFollow: boolean;
  geofences: Geofence[];
  geofenceEditMode: boolean;
  geofenceVertices: [number, number][];
  trackingPanelOpen: boolean;
  followEntityId: string | null;
  followMode: FollowMode;

  setViewState: (vs: Partial<MapViewState>) => void;
  toggleLayer: (layerId: string) => void;
  setSelectedEntityId: (id: string | null) => void;
  setMapEntities: (entities: MapEntity[]) => void;
  setIs3D: (is3D: boolean) => void;
  addTrackPoints: (entityId: string, points: TrackPoint[]) => void;
  removeTrack: (entityId: string) => void;
  updateEntityActivity: (entityId: string, activity: EntityActivity) => void;
  setPlaybackState: (state: PlaybackState) => void;
  setPlaybackTime: (time: number) => void;
  setPlaybackMaxTime: (maxTime: number) => void;
  setPlaybackSpeed: (speed: number) => void;
  setLiveFollow: (liveFollow: boolean) => void;
  togglePlayback: () => void;
  seekPlayback: (time: number) => void;
  addGeofence: (geofence: Geofence) => void;
  removeGeofence: (id: string) => void;
  setGeofenceEditMode: (editing: boolean) => void;
  addGeofenceVertex: (vertex: [number, number]) => void;
  removeLastVertex: () => void;
  clearGeofenceVertices: () => void;
  setTrackingPanelOpen: (open: boolean) => void;
  setFollowEntity: (id: string | null) => void;
  setFollowMode: (mode: FollowMode) => void;
}

export const useMapStore = create<MapState>((set, get) => ({
  viewState: {
    longitude: 0,
    latitude: 30,
    zoom: 2,
    bearing: 0,
    pitch: 0,
  },
  visibleLayers: new Set([
    'entities', 'connections', 'flights', 'vessels',
    'liveFlights', 'military', 'trackedAircraft', 'uavs',
    'earthquakes', 'activeFires', 'satellites',
  ]),
  selectedEntityId: null,
  activeTracks: new Map(),
  mapEntities: [],
  entityActivities: new Map(),
  is3D: false,
  playbackState: 'stopped',
  playbackTime: 0,
  playbackMaxTime: 1000,
  playbackSpeed: 1,
  liveFollow: true,
  geofences: [],
  geofenceEditMode: false,
  geofenceVertices: [],
  trackingPanelOpen: false,
  followEntityId: null,
  followMode: 'off',

  setViewState: (vs) => set((s) => ({ viewState: { ...s.viewState, ...vs } })),
  toggleLayer: (layerId) =>
    set((s) => {
      const layers = new Set(s.visibleLayers);
      if (layers.has(layerId)) {
        layers.delete(layerId);
      } else {
        layers.add(layerId);
      }
      return { visibleLayers: layers };
    }),
  setSelectedEntityId: (id) => set({ selectedEntityId: id }),
  setMapEntities: (entities) => set({ mapEntities: entities }),
  setIs3D: (is3D) => set({ is3D }),
  addTrackPoints: (entityId, points) =>
    set((s) => {
      const MAX_TRACK_POINTS = 2000;
      const tracks = new Map(s.activeTracks);
      const existing = tracks.get(entityId) || [];
      const combined = [...existing, ...points];
      tracks.set(entityId, combined.length > MAX_TRACK_POINTS
        ? combined.slice(combined.length - MAX_TRACK_POINTS)
        : combined);

      // Auto-extract activity from latest point
      const activities = new Map(s.entityActivities);
      const latest = points[points.length - 1];
      const meta = latest?.metadata as Record<string, unknown> | undefined;
      if (meta?.activity) {
        activities.set(entityId, {
          activity: String(meta.activity),
          activityType: String(meta.activityType || 'idle'),
          timestamp: latest.timestamp,
        });
      }

      // Auto-center camera when following this entity
      const followUpdate: Partial<MapState> = {};
      if (s.followEntityId === entityId && s.followMode !== 'off' && points.length > 0) {
        const latestPt = points[points.length - 1];
        followUpdate.viewState = {
          ...s.viewState,
          longitude: latestPt.position.longitude,
          latitude: latestPt.position.latitude,
          ...(s.followMode === 'track'
            ? {
              bearing: latestPt.heading ?? s.viewState.bearing,
              pitch: 60,       // Cinematic 3D angle
              zoom: Math.max(s.viewState.zoom, 16.5), // Ensure zoom is deep enough to see 3D buildings and drops
            }
            : {}),
        };
      }

      return { activeTracks: tracks, entityActivities: activities, ...followUpdate };
    }),
  removeTrack: (entityId) =>
    set((s) => {
      const tracks = new Map(s.activeTracks);
      tracks.delete(entityId);
      return { activeTracks: tracks };
    }),
  updateEntityActivity: (entityId, activity) =>
    set((s) => {
      const activities = new Map(s.entityActivities);
      activities.set(entityId, activity);
      return { entityActivities: activities };
    }),
  setPlaybackState: (playbackState) => set({ playbackState }),
  setPlaybackTime: (playbackTime) => set({ playbackTime }),
  setPlaybackMaxTime: (playbackMaxTime) => {
    set({ playbackMaxTime });
    if (_animator) _animator.setMaxTime(playbackMaxTime);
  },
  setPlaybackSpeed: (playbackSpeed) => {
    set({ playbackSpeed });
    if (_animator) _animator.setSpeed(playbackSpeed);
  },
  setLiveFollow: (liveFollow) => set({ liveFollow }),
  togglePlayback: () => {
    const state = get();
    if (!_animator) {
      _animator = new TrackAnimator(
        (time) => set({ playbackTime: time }),
        state.playbackMaxTime,
      );
    }
    _animator.setSpeed(state.playbackSpeed);
    _animator.toggle();
    set({ playbackState: _animator.playing ? 'playing' : 'paused', liveFollow: false });
  },
  seekPlayback: (time) => {
    if (!_animator) {
      _animator = new TrackAnimator(
        (t) => set({ playbackTime: t }),
        get().playbackMaxTime,
      );
    }
    _animator.seek(time);
    set({ liveFollow: false });
  },
  addGeofence: (geofence) => set((s) => ({ geofences: [...s.geofences, geofence] })),
  removeGeofence: (id) => set((s) => ({ geofences: s.geofences.filter((g) => g.id !== id) })),
  setGeofenceEditMode: (geofenceEditMode) => set({ geofenceEditMode }),
  addGeofenceVertex: (vertex) =>
    set((s) => ({ geofenceVertices: [...s.geofenceVertices, vertex] })),
  removeLastVertex: () =>
    set((s) => ({ geofenceVertices: s.geofenceVertices.slice(0, -1) })),
  clearGeofenceVertices: () => set({ geofenceVertices: [] }),
  setTrackingPanelOpen: (trackingPanelOpen) => set({ trackingPanelOpen }),
  setFollowEntity: (followEntityId) => set({ followEntityId }),
  setFollowMode: (followMode) => set({ followMode }),
}));

/** Initialize the playback animator. */
export function initAnimator() {
  if (_animator) return;
  const store = useMapStore.getState();
  _animator = new TrackAnimator(
    (time) => useMapStore.setState({ playbackTime: time }),
    store.playbackMaxTime,
  );
  _animator.setSpeed(store.playbackSpeed);
}

/** Destroy the playback animator. */
export function destroyAnimator() {
  if (_animator) {
    _animator.destroy();
    _animator = null;
  }
  useMapStore.setState({ playbackState: 'stopped', playbackTime: 0 });
}
