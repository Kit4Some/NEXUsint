import { useMutation, useQuery } from '@tanstack/react-query';
import { investigations } from '@/services/api';

export function useInvestigation(id: string | null) {
  return useQuery({
    queryKey: ['investigation', id],
    queryFn: () => investigations.get(id!),
    enabled: !!id,
    refetchInterval: 5000,
  });
}

export function useCreateInvestigation() {
  return useMutation({
    mutationFn: (data: { query: string; target_ints: string[]; priority?: string }) =>
      investigations.create(data),
  });
}

export function useExecuteInvestigation() {
  return useMutation({
    mutationFn: (id: string) => investigations.execute(id),
  });
}
