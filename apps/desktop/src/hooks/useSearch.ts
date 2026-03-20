import { useQuery } from '@tanstack/react-query';
import { search } from '@/services/api';

export function useFulltextSearch(
  query: string,
  filters?: { type?: string; source_int?: string; min_confidence?: number; limit?: number; offset?: number },
) {
  return useQuery({
    queryKey: ['search', 'fulltext', query, filters],
    queryFn: () => search.fulltext(query, filters),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });
}

export function useSemanticSearch(query: string, topK = 20, threshold = 0.7) {
  return useQuery({
    queryKey: ['search', 'semantic', query, topK, threshold],
    queryFn: () => search.semantic(query, topK, threshold),
    enabled: query.length >= 3,
    staleTime: 60_000,
  });
}

export function useSearchSuggestions(prefix: string, size = 10) {
  return useQuery({
    queryKey: ['search', 'suggest', prefix, size],
    queryFn: () => search.suggest(prefix, size),
    enabled: prefix.length >= 1,
    staleTime: 15_000,
  });
}
