import { useQuery } from '@tanstack/react-query';
import { entities as entitiesApi } from '@/services/api';

export function useEntityTimeline(entityId: string | null) {
  return useQuery({
    queryKey: ['timeline', entityId],
    queryFn: () => entitiesApi.getTimeline(entityId!),
    enabled: !!entityId,
  });
}

export function useInvestigationTimeline(investigationId: string | null) {
  return useQuery({
    queryKey: ['investigation-timeline', investigationId],
    queryFn: async () => {
      if (!investigationId) return [];
      const res = await fetch(
        `http://localhost:8000/api/v1/investigations/${investigationId}/report`,
      );
      if (!res.ok) return [];
      const report = await res.json();
      return report.entities ?? [];
    },
    enabled: !!investigationId,
  });
}
