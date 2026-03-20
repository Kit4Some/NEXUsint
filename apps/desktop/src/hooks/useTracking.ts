import { useCallback, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { sigint } from '@/services/api';
import { useMapStore } from '@/stores/useMapStore';
import type { TrackPoint } from '@/types';

export function useActiveFlights(bbox: { south: number; west: number; north: number; east: number } | null) {
  return useQuery({
    queryKey: ['flights', bbox],
    queryFn: () => sigint.getFlights(bbox!),
    enabled: !!bbox,
    refetchInterval: 10000, // Poll every 10s
  });
}

export function useActiveVessels(bbox: { south: number; west: number; north: number; east: number } | null) {
  return useQuery({
    queryKey: ['vessels', bbox],
    queryFn: () => sigint.getVessels(bbox!),
    enabled: !!bbox,
    refetchInterval: 10000,
  });
}

export function useTrack(entityId: string | null, entityType: 'flight' | 'vessel' = 'flight') {
  const { activeTracks } = useMapStore();

  const { data } = useQuery({
    queryKey: ['track', entityId, entityType],
    queryFn: async () => {
      if (!entityId) return null;
      if (entityType === 'flight') {
        return sigint.getFlightTrack(entityId);
      }
      return sigint.getVesselTrack(entityId);
    },
    enabled: !!entityId,
    refetchInterval: 30000,
  });

  // Update activeTracks store when data arrives
  useEffect(() => {
    if (data && entityId) {
      const store = useMapStore.getState();
      const tracks = new Map(store.activeTracks);
      const points: TrackPoint[] = ((data as { track?: unknown[] })?.track ?? []).map((p: unknown) => p as TrackPoint);
      tracks.set(entityId, points);
      store.addTrackPoints(entityId, points);
    }
  }, [data, entityId]);

  return {
    track: entityId ? activeTracks.get(entityId) ?? [] : [],
  };
}
