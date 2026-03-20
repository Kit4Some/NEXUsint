import { io, Socket } from 'socket.io-client';
import { useAppStore } from '@/stores/useAppStore';
import { useInvestigationStore } from '@/stores/useInvestigationStore';
import { useCollectionStore } from '@/stores/useCollectionStore';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';

import { API_HOST } from '@/services/api';

const WS_URL = API_HOST;

let socket: Socket | null = null;
let permanentlyFailed = false;

export function connectWebSocket(token?: string) {
  // Don't reconnect if previous attempts exhausted
  if (permanentlyFailed) return;
  if (socket?.connected) return;
  // Clean up any existing disconnected socket
  if (socket) {
    socket.removeAllListeners();
    socket.disconnect();
    socket = null;
  }

  socket = io(WS_URL, {
    transports: ['polling', 'websocket'],
    reconnection: true,
    reconnectionDelay: 5000,
    reconnectionDelayMax: 30000,
    reconnectionAttempts: 10,
    timeout: 10000,
    autoConnect: true,
    // Pass JWT token via both auth object and query param for max compatibility
    auth: token ? { token } : undefined,
    query: token ? { token } : undefined,
  });

  socket.on('connect', () => {
    permanentlyFailed = false;
    useAppStore.getState().setConnectionStatus('connected');
    socket?.emit('subscribe_alerts', {});
    socket?.emit('subscribe_live_map', {});
    socket?.emit('subscribe_live_feed', {});
  });

  socket.on('disconnect', () => {
    useAppStore.getState().setConnectionStatus('disconnected');
  });

  socket.on('connect_error', () => {
    useAppStore.getState().setConnectionStatus('disconnected');
  });

  socket.on('reconnect_failed', () => {
    permanentlyFailed = true;
    useAppStore.getState().setConnectionStatus('disconnected');
    console.warn('[WebSocket] Reconnection attempts exhausted. Call reconnectWebSocket() to retry.');
    // Clean up to stop any further attempts
    socket?.removeAllListeners();
    socket?.disconnect();
    socket = null;
  });

  // Investigation progress
  socket.on('investigation:progress', (data: {
    investigationId: string;
    agentName: string;
    status: string;
    progress: number;
    message: string;
  }) => {
    const store = useInvestigationStore.getState();
    store.setProgress(data.progress);
    store.updateAgentState({
      name: data.agentName,
      status: data.status as 'waiting' | 'running' | 'completed' | 'failed',
      itemsProcessed: 0,
    });
    store.addLogEntry({
      timestamp: new Date().toISOString(),
      level: 'info',
      agent: data.agentName,
      message: data.message,
    });
  });

  // New entity discovered (from investigation or collection)
  socket.on('entity:new', (data: { id: string; type: string; name: string; confidence: number; sourceInt?: string }) => {
    useInvestigationStore.getState().addDiscoveredEntity(data);
    useCollectionStore.getState().addRecentEntity({
      id: data.id,
      type: data.type,
      name: data.name,
      confidence: data.confidence,
      sourceInt: data.sourceInt || 'UNKNOWN',
    });
    useAppStore.getState().setLastUpdate(new Date().toLocaleTimeString());
  });

  // Collection progress (real-time from Celery via Redis bridge)
  socket.on('collection:progress', (data: {
    jobId: string;
    intType?: string;
    status?: string;
    progress: number;
    entitiesCreated?: number;
    totalResults?: number;
    query?: string;
  }) => {
    useCollectionStore.getState().updateJob(data.jobId, {
      status: (data.status as 'queued' | 'running') || 'running',
      progress: data.progress,
      resultCount: data.entitiesCreated || 0,
    });
  });

  // Collection completed
  socket.on('collection:completed', (data: {
    jobId: string;
    intType: string;
    query: string;
    resultCount: number;
  }) => {
    useCollectionStore.getState().updateJob(data.jobId, {
      status: 'completed',
      progress: 100,
      resultCount: data.resultCount,
    });
    useAppStore.getState().setLastUpdate(new Date().toLocaleTimeString());
  });

  // Collection failed
  socket.on('collection:failed', (data: {
    jobId: string;
    error: string;
  }) => {
    useCollectionStore.getState().updateJob(data.jobId, {
      status: 'failed',
      error: data.error,
    });
  });

  // Pivot events — auto-pivot child job dispatched
  socket.on('pivot:dispatched', (data: {
    parentJobId: string;
    childJobId: string;
    entityType: string;
    entityName: string;
    scanType: string;
    intType: string;
    pivotDepth: number;
  }) => {
    useCollectionStore.getState().addPivotChild(data.parentJobId, data);
  });

  // Persistent alerts
  socket.on('alert:received', (data: {
    id: string;
    entityId: string;
    entityName: string;
    alertType: string;
    severity: string;
    title: string;
    description: string;
    createdAt: string;
  }) => {
    // Dynamic import to avoid circular dependency
    import('@/stores/useMonitoringStore').then(({ useMonitoringStore }) => {
      useMonitoringStore.getState().addAlert(data);
    });
    // Desktop notification for high/critical
    if (['critical', 'high'].includes(data.severity) && Notification.permission === 'granted') {
      new Notification(`NEXUS Alert: ${data.title}`, { body: data.description });
    }
  });

  // Live feed events
  socket.on('livefeed:flights', (data: { flights: unknown[]; tracked: unknown[] }) => {
    const lf = useLiveFeedStore.getState();
    lf.setFlights(data.flights as any);
    lf.setTrackedFlights(data.tracked as any);
  });

  socket.on('livefeed:military', (data: { military: unknown[]; uavs: unknown[] }) => {
    const lf = useLiveFeedStore.getState();
    lf.setMilitaryFlights(data.military as any);
    lf.setUavs(data.uavs as any);
  });

  socket.on('livefeed:news', (data: { articles: unknown[] }) => {
    useLiveFeedStore.getState().setNews(data.articles as any);
  });

  socket.on('livefeed:earthquakes', (data: { earthquakes: unknown[] }) => {
    useLiveFeedStore.getState().setEarthquakes(data.earthquakes as any);
  });

  socket.on('livefeed:fires', (data: { fires: unknown[] }) => {
    useLiveFeedStore.getState().setFires(data.fires as any);
  });

  socket.on('livefeed:stocks', (data: { stocks: Record<string, unknown> }) => {
    useLiveFeedStore.getState().setStocks(data.stocks as any);
  });

  socket.on('livefeed:oil', (data: { oil: Record<string, unknown> }) => {
    useLiveFeedStore.getState().setOil(data.oil as any);
  });

  socket.on('livefeed:jamming', (data: { zones: unknown[] }) => {
    useLiveFeedStore.getState().setGpsJamming(data.zones as any);
  });

  socket.on('livefeed:weather', (data: { radar: unknown }) => {
    useLiveFeedStore.getState().setWeatherRadar(data.radar as any);
  });

  socket.on('livefeed:status', (data: { source_timestamps: Record<string, string> }) => {
    const lf = useLiveFeedStore.getState();
    lf.setSourceTimestamps(data.source_timestamps);
    lf.setActive(true);
  });

  socket.on('livefeed:satellites', (data: { satellites: unknown[] }) => {
    useLiveFeedStore.getState().setSatellites(data.satellites as any);
  });

  socket.on('livefeed:gdelt', (data: { events: unknown[] }) => {
    useLiveFeedStore.getState().setGdelt(data.events as any);
  });

  socket.on('livefeed:frontlines', (data: { geojson: unknown }) => {
    useLiveFeedStore.getState().setFrontlines(data.geojson);
  });

  socket.on('livefeed:outages', (data: { outages: unknown[] }) => {
    useLiveFeedStore.getState().setInternetOutages(data.outages as any);
  });

  // Community updated — trigger graph refresh
  socket.on('community:updated', (data: { communities: number; jobId?: string }) => {
    useAppStore.getState().setLastUpdate(new Date().toLocaleTimeString());
  });

  // Track batch updates (flight/vessel positions + activity context)
  socket.on('track:batch_update', (data: { tracks: Array<{ entityId: string; position: { position: { latitude: number; longitude: number }; timestamp: string; speed?: number; heading?: number; metadata?: Record<string, unknown> }; activity?: string; activityType?: string; entityType?: string; trigger?: string }> }) => {
    import('@/stores/useMapStore').then(({ useMapStore }) => {
      const mapStore = useMapStore.getState();
      for (const track of data.tracks) {
        // Inject activity into metadata for store extraction
        const point = { ...track.position };
        if (track.activity || track.activityType || track.entityType) {
          (point as any).metadata = {
            ...(point as any).metadata,
            activity: track.activity,
            activityType: track.activityType,
            entityType: track.entityType,
            trigger: track.trigger,
          };
        }
        mapStore.addTrackPoints(track.entityId, [point]);

        // Update entity activity directly if provided
        if (track.activity) {
          mapStore.updateEntityActivity(track.entityId, {
            activity: track.activity,
            activityType: track.activityType || 'idle',
            timestamp: track.position.timestamp,
          });
        }
      }

      // Recalculate playbackMaxTime based on longest track length
      const maxLen = Math.max(...Array.from(mapStore.activeTracks.values()).map((t) => t.length));
      if (maxLen > 0) {
        const newMaxTime = Math.max(1000, maxLen * 2);
        if (newMaxTime !== mapStore.playbackMaxTime) {
          mapStore.setPlaybackMaxTime(newMaxTime);
        }
      }

      // Auto-advance playback to latest when liveFollow is enabled
      if (mapStore.liveFollow) {
        mapStore.setPlaybackTime(mapStore.playbackMaxTime);
      }
    });
  });

  return socket;
}

export function disconnectWebSocket() {
  socket?.removeAllListeners();
  socket?.disconnect();
  socket = null;
}

/** Reset failed state and attempt a fresh connection. */
export function reconnectWebSocket(token?: string) {
  permanentlyFailed = false;
  disconnectWebSocket();
  connectWebSocket(token);
}

export function joinInvestigation(investigationId: string) {
  socket?.emit('join_investigation', { investigationId });
}

export function leaveInvestigation(investigationId: string) {
  socket?.emit('leave_investigation', { investigationId });
}

export function getSocket(): Socket | null {
  return socket;
}
