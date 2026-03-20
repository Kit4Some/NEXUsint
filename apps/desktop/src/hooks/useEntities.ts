import { useQuery } from '@tanstack/react-query';
import { entities } from '@/services/api';

export function useEntitySearch(params: Record<string, string | number | undefined>) {
  return useQuery({
    queryKey: ['entities', params],
    queryFn: () => entities.search(params),
    enabled: Object.values(params).some((v) => v !== undefined),
  });
}

export function useEntity(id: string | null) {
  return useQuery({
    queryKey: ['entity', id],
    queryFn: () => entities.get(id!),
    enabled: !!id,
  });
}

export function useEntityGraph(id: string | null, depth = 2) {
  return useQuery({
    queryKey: ['entity-graph', id, depth],
    queryFn: () => entities.getGraph(id!, depth),
    enabled: !!id,
  });
}

export function useEntityTimeline(id: string | null) {
  return useQuery({
    queryKey: ['entity-timeline', id],
    queryFn: () => entities.getTimeline(id!),
    enabled: !!id,
  });
}
