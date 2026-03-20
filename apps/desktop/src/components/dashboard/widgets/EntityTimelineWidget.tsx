import { useInvestigationStore } from '@/stores/useInvestigationStore';
import { useQuery } from '@tanstack/react-query';
import { entities as entitiesApi } from '@/services/api';
import { Card } from '@/components/common/Card';

export function EntityTimelineWidget() {
  const { discoveredEntities } = useInvestigationStore();

  // Fallback: fetch from API when in-memory store is empty
  const { data: apiEntities } = useQuery({
    queryKey: ['entities', 'recent-timeline'],
    queryFn: () => entitiesApi.search({ limit: 20, sort: 'last_seen' }),
    enabled: discoveredEntities.length === 0,
    staleTime: 30_000,
  });

  const storeEntities = discoveredEntities.slice(-20).reverse();
  const fallbackEntities = (apiEntities as Array<{ type: string; name: string }> || []).map((e) => ({
    type: e.type || 'Unknown',
    name: e.name || 'Unnamed',
  }));
  const recent = storeEntities.length > 0 ? storeEntities : fallbackEntities;

  const typeColors: Record<string, string> = {
    IPAddress: 'text-red-400',
    Domain: 'text-green-400',
    Person: 'text-blue-400',
    Organization: 'text-purple-400',
    ThreatActor: 'text-amber-400',
    Location: 'text-cyan-400',
    Aircraft: 'text-orange-400',
    Vessel: 'text-teal-400',
  };

  return (
    <Card className="p-4">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
        Recent Discoveries
      </p>

      <div className="space-y-1 max-h-[200px] overflow-y-auto">
        {recent.map((ent, i) => (
          <div key={i} className="flex items-center gap-2 py-0.5">
            <span className="text-[10px] font-mono text-nexus-text-secondary w-12 flex-shrink-0">
              {new Date().toLocaleTimeString().slice(0, 5)}
            </span>
            <span className={`text-[10px] font-mono ${typeColors[ent.type] || 'text-gray-400'}`}>
              [{ent.type}]
            </span>
            <span className="text-xs font-mono text-nexus-text-primary truncate">
              {ent.name}
            </span>
          </div>
        ))}

        {recent.length === 0 && (
          <p className="text-[10px] font-mono text-nexus-text-secondary text-center py-4">
            No recent discoveries
          </p>
        )}
      </div>
    </Card>
  );
}
