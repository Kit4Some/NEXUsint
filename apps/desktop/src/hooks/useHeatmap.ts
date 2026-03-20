import { useQuery } from '@tanstack/react-query';
import { map } from '@/services/api';

export function useHeatmapData(bbox: { west: number; south: number; east: number; north: number } | null) {
  return useQuery({
    queryKey: ['map', 'heatmap', bbox],
    queryFn: () => map.getHeatmap(bbox!),
    enabled: !!bbox,
    staleTime: 60_000,
  });
}
