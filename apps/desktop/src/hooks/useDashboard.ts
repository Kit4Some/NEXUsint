import { useQuery } from '@tanstack/react-query';
import { dashboard } from '@/services/api';

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      try {
        return await dashboard.stats();
      } catch (err) {
        console.error('[Dashboard] Stats fetch failed:', err);
        throw err;
      }
    },
    refetchInterval: 30_000,
    staleTime: 15_000,
    retry: 3,
  });
}

export function useRecentInvestigations(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ['dashboard', 'recent-investigations', params],
    queryFn: () => dashboard.recentInvestigations(params),
    staleTime: 15_000,
  });
}
