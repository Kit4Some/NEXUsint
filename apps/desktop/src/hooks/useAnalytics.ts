import { useQuery } from '@tanstack/react-query';
import { analytics } from '../services/api';

export function useAnomalyDetection(methods?: string) {
  return useQuery({
    queryKey: ['analytics', 'anomalies', 'advanced', methods],
    queryFn: () => analytics.advancedAnomalies(methods),
    staleTime: 60_000,
  });
}

export function useCommunityInsights() {
  return useQuery({
    queryKey: ['analytics', 'communities', 'enhanced'],
    queryFn: () => analytics.enhancedCommunities(),
    staleTime: 60_000,
  });
}

export function useTemporalAnalysis(entityId: string | null) {
  return useQuery({
    queryKey: ['analytics', 'temporal', entityId],
    queryFn: () => analytics.temporalAnalysis(entityId!),
    enabled: !!entityId,
    staleTime: 30_000,
  });
}
