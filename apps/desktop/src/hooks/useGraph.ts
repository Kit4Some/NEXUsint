import { useQuery } from '@tanstack/react-query';
import { entities as entitiesApi, analytics } from '@/services/api';

export function useSubgraph(entityId: string | null, depth = 2) {
  return useQuery({
    queryKey: ['subgraph', entityId, depth],
    queryFn: () => entitiesApi.getGraph(entityId!, depth),
    enabled: !!entityId,
  });
}

export function useCommunities() {
  return useQuery({
    queryKey: ['communities'],
    queryFn: () => analytics.communityDetection(),
  });
}

export function useCentrality(algo = 'pagerank') {
  return useQuery({
    queryKey: ['centrality', algo],
    queryFn: () => analytics.centrality(algo),
  });
}

export function useShortestPath(fromId: string | null, toId: string | null) {
  return useQuery({
    queryKey: ['shortest-path', fromId, toId],
    queryFn: async () => {
      const params = new URLSearchParams({ from: fromId!, to: toId! });
      const res = await fetch(`http://localhost:8000/api/v1/analytics/shortest-path?${params}`);
      return res.json();
    },
    enabled: !!fromId && !!toId,
  });
}
