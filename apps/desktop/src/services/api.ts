export const API_PORT = (import.meta as any).env?.VITE_API_PORT || '8000';
export const API_HOST = `http://localhost:${API_PORT}`;
const API_BASE = `${API_HOST}/api/v1`;

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  if (isRefreshing && refreshPromise) return refreshPromise;
  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const { useAuthStore } = await import('@/stores/useAuthStore');
      return await useAuthStore.getState().refreshTokens();
    } catch {
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    // Attempt token refresh on 401 (except for auth endpoints)
    if (response.status === 401 && !path.startsWith('/auth/')) {
      const refreshed = await attemptTokenRefresh();
      if (refreshed) {
        return request(path, options);
      }
      const { useAuthStore } = await import('@/stores/useAuthStore');
      useAuthStore.getState().logout();
      throw new Error('Session expired');
    }

    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auth
export const auth = {
  login: (username: string, password: string) =>
    request<{ access_token: string; refresh_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () =>
    request<{ detail: string }>('/auth/logout', { method: 'POST' }),
  refresh: (refreshTokenValue: string) => {
    const prevToken = accessToken;
    setAccessToken(refreshTokenValue);
    return request<{ access_token: string; refresh_token: string }>('/auth/refresh', {
      method: 'POST',
    }).finally(() => {
      if (accessToken === refreshTokenValue) setAccessToken(prevToken);
    });
  },
  me: () => request<{ id: string; username: string; email: string; role: string }>('/auth/me'),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<{ detail: string }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
  register: (username: string, email: string, password: string, passwordConfirm: string) =>
    request<{ access_token: string; refresh_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password, password_confirm: passwordConfirm }),
    }),
};

// Entities
export const entities = {
  search: (params: Record<string, string | number | undefined>) => {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) searchParams.set(key, String(value));
    }
    return request<unknown[]>(`/entities?${searchParams}`);
  },
  get: (id: string) => request<unknown>(`/entities/${id}`),
  getGraph: (id: string, depth = 2) => request<unknown>(`/entities/${id}/graph?depth=${depth}`),
  getTimeline: (id: string) => request<unknown[]>(`/entities/${id}/timeline`),
  generateDossier: (id: string) =>
    request<{ entity_id: string; entity_name: string; dossier_markdown: string; data: unknown }>(
      `/entities/${id}/dossier`, { method: 'POST' },
    ),
  getSuggestions: (id: string) =>
    request<{ entity_id: string; suggestions: Array<{ int_type: string; scan_type: string; query: string; reason: string }> }>(
      `/entities/${id}/suggestions`,
    ),
};

// Map
export const map = {
  getEntities: (bbox: { west: number; south: number; east: number; north: number }, types?: string) => {
    const params = new URLSearchParams({
      west: String(bbox.west),
      south: String(bbox.south),
      east: String(bbox.east),
      north: String(bbox.north),
    });
    if (types) params.set('types', types);
    return request<unknown[]>(`/map/entities?${params}`);
  },
  getHeatmap: (bbox: { west: number; south: number; east: number; north: number }) =>
    request<unknown[]>(`/map/heatmap?west=${bbox.west}&south=${bbox.south}&east=${bbox.east}&north=${bbox.north}`),
  getTracks: (entityId: string) => request<unknown>(`/map/tracks/${entityId}`),
  getConnections: (bbox: { west: number; south: number; east: number; north: number }) => {
    const params = new URLSearchParams({
      west: String(bbox.west), south: String(bbox.south),
      east: String(bbox.east), north: String(bbox.north),
    });
    return request<Array<{
      source: { id: string; longitude: number; latitude: number; type: string };
      target: { id: string; longitude: number; latitude: number; type: string };
      rel_type: string;
      confidence: number;
    }>>(`/map/connections?${params}`);
  },
  getClusters: (bbox: { west: number; south: number; east: number; north: number }, zoom: number) => {
    const params = new URLSearchParams({
      west: String(bbox.west), south: String(bbox.south),
      east: String(bbox.east), north: String(bbox.north),
      zoom: String(zoom),
    });
    return request<Array<{
      id: string;
      position: { latitude: number; longitude: number };
      count: number;
      entityTypes: Record<string, number>;
    }>>(`/map/clusters?${params}`);
  },
};

// Investigations
export const investigations = {
  create: (data: { query: string; target_ints: string[]; priority?: string }) =>
    request<unknown>('/investigations', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => request<unknown>(`/investigations/${id}`),
  execute: (id: string) =>
    request<unknown>(`/investigations/${id}/execute`, { method: 'POST' }),
  getStatus: (id: string) => request<unknown>(`/investigations/${id}/status`),
  getReport: (id: string) => request<unknown>(`/investigations/${id}/report`),
};

// Collection
export const collection = {
  cybint: (data: { query: string; scan_type: string; auto_pivot?: boolean }) =>
    request<unknown>('/collect/cybint', { method: 'POST', body: JSON.stringify(data) }),
  socmint: (data: { query: string; scan_type: string; auto_pivot?: boolean }) =>
    request<unknown>('/collect/socmint', { method: 'POST', body: JSON.stringify(data) }),
  sigint: (data: { query: string; scan_type: string; auto_pivot?: boolean }) =>
    request<unknown>('/collect/sigint', { method: 'POST', body: JSON.stringify(data) }),
  geoint: (data: { query: string; scan_type: string; auto_pivot?: boolean }) =>
    request<unknown>('/collect/geoint', { method: 'POST', body: JSON.stringify(data) }),
  getStatus: (jobId: string) => request<unknown>(`/collect/status/${jobId}`),
  getTree: (jobId: string) => request<unknown[]>(`/collect/tree/${jobId}`),
  getHistory: (params?: { limit?: number; offset?: number; int_type?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    if (params?.offset !== undefined) sp.set('offset', String(params.offset));
    if (params?.int_type) sp.set('int_type', params.int_type);
    if (params?.status) sp.set('status', params.status);
    return request<{ jobs: Array<{ id: string; int_type: string; query: string; scan_type: string; status: string; progress: number; result_count: number; error: string | null; parent_job_id: string | null; pivot_depth: number; auto_pivot: boolean; created_at: string | null; completed_at: string | null }>; total: number; limit: number; offset: number }>(`/collect/history?${sp}`);
  },
  getJobEntities: (jobId: string) =>
    request<Array<{ id: string; name: string; type: string; confidence: number; sourceInt: string; riskScore: number }>>(`/collect/jobs/${jobId}/entities`),
};

// Analytics
export const analytics = {
  communityDetection: () => request<unknown>('/analytics/community-detection'),
  centrality: (algo = 'pagerank') => request<unknown>(`/analytics/centrality?algo_name=${algo}`),
  anomalies: () => request<unknown>('/analytics/anomalies'),
  shortestPath: (fromId: string, toId: string) =>
    request<unknown>(`/analytics/shortest-path?from=${encodeURIComponent(fromId)}&to=${encodeURIComponent(toId)}`),
  advancedAnomalies: (methods?: string) => {
    const params = methods ? `?methods=${encodeURIComponent(methods)}` : '';
    return request<unknown>(`/analytics/anomalies/advanced${params}`);
  },
  getCommunities: () => request<Array<{ community_id: number; members: Array<{ id: string; name: string; type: string; riskScore: number }>; member_count: number }>>('/analytics/communities'),
  enhancedCommunities: () => request<unknown>('/analytics/communities/enhanced'),
  communityDetails: (id: number) => request<unknown>(`/analytics/communities/${id}/details`),
  temporalAnalysis: (entityId: string) => request<unknown>(`/analytics/temporal/${entityId}`),
};

// SIGINT
export const sigint = {
  getFlights: (bbox: { south: number; west: number; north: number; east: number }) =>
    request<unknown>(`/sigint/flights?south=${bbox.south}&west=${bbox.west}&north=${bbox.north}&east=${bbox.east}`),
  getFlightTrack: (icao24: string) => request<unknown>(`/sigint/flights/${icao24}/track`),
  getVessels: (bbox: { south: number; west: number; north: number; east: number }) =>
    request<unknown>(`/sigint/vessels?south=${bbox.south}&west=${bbox.west}&north=${bbox.north}&east=${bbox.east}`),
  getVesselTrack: (mmsi: string) => request<unknown>(`/sigint/vessels/${mmsi}/track`),
};

// SOCMINT
export const socmint = {
  usernameSearch: (username: string) =>
    request<unknown>('/socmint/username-search', {
      method: 'POST',
      body: JSON.stringify({ username }),
    }),
};

// Reports
export const reports = {
  generate: (investigationId: string, format = 'json', sections?: string) => {
    const params = new URLSearchParams({ format });
    if (sections) params.set('sections', sections);
    return request<unknown>(`/reports/generate/${investigationId}?${params}`, { method: 'POST' });
  },
  get: (investigationId: string, format = 'json') =>
    request<unknown>(`/reports/${investigationId}?format=${format}`),
  preview: (investigationId: string) =>
    request<unknown>(`/reports/${investigationId}/preview`),
};

// STIX
export const stix = {
  exportInvestigation: (investigationId: string) =>
    request<unknown>(`/stix/export/investigation/${investigationId}`),
  exportEntity: (entityId: string, depth = 1) =>
    request<unknown>(`/stix/export/entity/${entityId}?depth=${depth}`),
  importBundle: (bundle: unknown) =>
    request<unknown>('/stix/import', { method: 'POST', body: JSON.stringify(bundle) }),
  validate: (bundle: unknown) =>
    request<unknown>('/stix/validate', { method: 'POST', body: JSON.stringify(bundle) }),
};

// GEOINT
export const geoint = {
  searchSatellite: (bbox: { south: number; west: number; north: number; east: number }, options?: { dateStart?: string; dateEnd?: string; maxCloudCover?: number }) => {
    const params = new URLSearchParams({ south: String(bbox.south), west: String(bbox.west), north: String(bbox.north), east: String(bbox.east) });
    if (options?.dateStart) params.set('date_start', options.dateStart);
    if (options?.dateEnd) params.set('date_end', options.dateEnd);
    if (options?.maxCloudCover !== undefined) params.set('max_cloud_cover', String(options.maxCloudCover));
    return request<unknown[]>(`/geoint/satellite/search?${params}`);
  },
  getOsmFeatures: (bbox: { south: number; west: number; north: number; east: number }, tags?: string) => {
    const params = new URLSearchParams({ south: String(bbox.south), west: String(bbox.west), north: String(bbox.north), east: String(bbox.east) });
    if (tags) params.set('tags', tags);
    return request<unknown[]>(`/geoint/osm/features?${params}`);
  },
  geocodeForward: (query: string) =>
    request<unknown>(`/geoint/geocode/forward?q=${encodeURIComponent(query)}`),
  geocodeReverse: (lat: number, lon: number) =>
    request<unknown>(`/geoint/geocode/reverse?lat=${lat}&lon=${lon}`),
};

// Dashboard
export const dashboard = {
  stats: () =>
    request<{
      threat_level: string;
      threat_score: number;
      total_entities: number;
      int_coverage: Record<string, number>;
      active_collections: Array<{ id: string; int_type: string; query: string; scan_type: string; progress: number; status: string }>;
      confidence_distribution: Array<{ bucket: string; count: number }>;
    }>('/dashboard/stats'),
  recentInvestigations: (params?: { status?: string; limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));
    const qs = searchParams.toString();
    return request<{
      total: number;
      items: Array<{ id: string; query: string; status: string; priority: string; entity_count: number; created_at: string; updated_at: string }>;
    }>(`/dashboard/recent-investigations${qs ? `?${qs}` : ''}`);
  },
};

// Search
export const search = {
  fulltext: (q: string, filters?: { type?: string; source_int?: string; min_confidence?: number; limit?: number; offset?: number }) => {
    const params = new URLSearchParams({ q });
    if (filters?.type) params.set('type', filters.type);
    if (filters?.source_int) params.set('source_int', filters.source_int);
    if (filters?.min_confidence !== undefined) params.set('min_confidence', String(filters.min_confidence));
    if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
    if (filters?.offset !== undefined) params.set('offset', String(filters.offset));
    return request<{ total: number; hits: Array<{ id: string; name: string; type: string; score: number; highlights: Record<string, string[]> }> }>(`/search/fulltext?${params}`);
  },
  semantic: (q: string, topK = 20, threshold = 0.7) =>
    request<Array<{ entity_id: string; entity_type: string; entity_name: string; source_int: string; similarity: number }>>(`/search/semantic?q=${encodeURIComponent(q)}&top_k=${topK}&threshold=${threshold}`),
  suggest: (prefix: string, size = 10) =>
    request<Array<{ id: string; name: string; type: string }>>(`/search/suggest?prefix=${encodeURIComponent(prefix)}&size=${size}`),
  reindex: () =>
    request<{ detail: string }>('/search/reindex', { method: 'POST' }),
};

// Seed
export const seed = {
  demo: () => request<{ status: string; entities: number; relationships: number }>('/seed/demo', { method: 'POST' }),
};

// Chat
export const chat = {
  send: (message: string, context?: { entity_id?: string; investigation_id?: string }) =>
    request<{ response: string; entities?: Array<{ id: string; name: string; type: string }>; actions?: Array<{ type: string; label: string; params: Record<string, unknown> }> }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, context }),
    }),
};

// Ontology
export const ontology = {
  initialize: (owlUrl: string) =>
    request<{ detail: string }>('/ontology/initialize', { method: 'POST', body: JSON.stringify({ owl_url: owlUrl }) }),
  getClasses: () => request<unknown>('/ontology/classes'),
  getTracking: (entityId: string) => request<unknown>(`/ontology/tracking/${entityId}`),
  reason: (entityIds: string[], reasoningType: 'track' | 'correlate' | 'infer') =>
    request<unknown>('/ontology/reason', {
      method: 'POST',
      body: JSON.stringify({ entity_ids: entityIds, reasoning_type: reasoningType }),
    }),
};

// Live Feed
export const liveFeed = {
  getFast: () => request<unknown>('/live/fast'),
  getSlow: () => request<unknown>('/live/slow'),
  getHealth: () => request<unknown>('/live/health'),
  start: () => request<unknown>('/live/start', { method: 'POST' }),
  stop: () => request<unknown>('/live/stop', { method: 'POST' }),
  getNews: () => request<unknown>('/news/latest'),
  getFeeds: () => request<unknown>('/news/feeds'),
  updateFeeds: (feeds: unknown) =>
    request<unknown>('/news/feeds', { method: 'PUT', body: JSON.stringify(feeds) }),
  resetFeeds: () => request<unknown>('/news/feeds/reset', { method: 'POST' }),
};

// Fusion
export const fusion = {
  getCorrelationMatrix: () => request<unknown>('/fusion/correlation-matrix'),
  getEntityEvidence: (entityId: string) => request<unknown>(`/fusion/entity/${entityId}/evidence`),
  correlate: (entityIds: string[]) =>
    request<unknown>('/fusion/correlate', {
      method: 'POST',
      body: JSON.stringify(entityIds),
    }),
};

// Monitoring — watch list & alerts
export const monitoring = {
  listTargets: (activeOnly = true) =>
    request<unknown[]>(`/monitoring/targets?active_only=${activeOnly}`),
  createTarget: (data: {
    entity_id?: string; entity_name: string; entity_type: string;
    int_type: string; scan_type: string; query: string;
    interval_hours?: number; auto_pivot?: boolean;
  }) => request<unknown>('/monitoring/targets', { method: 'POST', body: JSON.stringify(data) }),
  updateTarget: (id: string, data: { interval_hours?: number; active?: boolean; auto_pivot?: boolean }) =>
    request<unknown>(`/monitoring/targets/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteTarget: (id: string) =>
    request<void>(`/monitoring/targets/${id}`, { method: 'DELETE' }),
  listAlerts: (params?: { unacknowledged_only?: boolean; severity?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.unacknowledged_only) sp.set('unacknowledged_only', 'true');
    if (params?.severity) sp.set('severity', params.severity);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    return request<unknown[]>(`/monitoring/alerts?${sp}`);
  },
  acknowledgeAlert: (id: string) =>
    request<unknown>(`/monitoring/alerts/${id}/acknowledge`, { method: 'PATCH' }),
  listAlertRules: () => request<unknown[]>('/monitoring/alerts/rules'),
  createAlertRule: (data: { name: string; rule_type: string; conditions: Record<string, unknown>; severity?: string }) =>
    request<unknown>('/monitoring/alerts/rules', { method: 'POST', body: JSON.stringify(data) }),
  deleteAlertRule: (id: string) =>
    request<void>(`/monitoring/alerts/rules/${id}`, { method: 'DELETE' }),
  // Live Feed
  startLiveFeed: (bbox: { lamin: number; lomin: number; lamax: number; lomax: number }) =>
    request<{ status: string; bbox: typeof bbox }>('/monitoring/live-feed/start', {
      method: 'POST', body: JSON.stringify(bbox),
    }),
  stopLiveFeed: () =>
    request<{ status: string }>('/monitoring/live-feed/stop', { method: 'POST' }),
  getLiveFeedStatus: () =>
    request<{ active: boolean; bbox: { lamin: number; lomin: number; lamax: number; lomax: number } | null; last_scan: { timestamp: string; aircraft_count: number; new_entities?: number } | null }>(
      '/monitoring/live-feed/status',
    ),
};
