import { useQuery } from '@tanstack/react-query';

const API_BASE = 'http://localhost:8000/api/v1';

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export function useSatelliteSearch(
  bbox: { south: number; west: number; north: number; east: number } | null,
  options?: { dateStart?: string; dateEnd?: string; maxCloudCover?: number },
) {
  const params = new URLSearchParams();
  if (bbox) {
    params.set('south', String(bbox.south));
    params.set('west', String(bbox.west));
    params.set('north', String(bbox.north));
    params.set('east', String(bbox.east));
  }
  if (options?.dateStart) params.set('date_start', options.dateStart);
  if (options?.dateEnd) params.set('date_end', options.dateEnd);
  if (options?.maxCloudCover !== undefined) params.set('max_cloud_cover', String(options.maxCloudCover));

  return useQuery({
    queryKey: ['geoint', 'satellite', bbox, options],
    queryFn: () => fetchJson<unknown[]>(`/geoint/satellite/search?${params}`),
    enabled: !!bbox,
    staleTime: 60_000,
  });
}

export function useOsmFeatures(
  bbox: { south: number; west: number; north: number; east: number } | null,
  tags?: string,
) {
  const params = new URLSearchParams();
  if (bbox) {
    params.set('south', String(bbox.south));
    params.set('west', String(bbox.west));
    params.set('north', String(bbox.north));
    params.set('east', String(bbox.east));
  }
  if (tags) params.set('tags', tags);

  return useQuery({
    queryKey: ['geoint', 'osm', bbox, tags],
    queryFn: () => fetchJson<unknown[]>(`/geoint/osm/features?${params}`),
    enabled: !!bbox,
    staleTime: 60_000,
  });
}

export function useGeocode(query: string | null) {
  return useQuery({
    queryKey: ['geoint', 'geocode', query],
    queryFn: () => fetchJson<unknown>(`/geoint/geocode/forward?q=${encodeURIComponent(query!)}`),
    enabled: !!query && query.length > 2,
    staleTime: 300_000,
  });
}
