import { useEntityStore } from '@/stores/useEntityStore';
import { ConfidenceBar } from '@/components/common/ConfidenceBar';

interface RelationsTabProps {
  entityId: string;
}

export function RelationsTab({ entityId }: RelationsTabProps) {
  const { entityRelationships } = useEntityStore();

  if (entityRelationships.length === 0) {
    return (
      <div className="p-3 text-sm text-nexus-text-secondary">
        <p>No relationships loaded.</p>
        <p className="mt-1 text-xs">
          Click "Deep Investigate" to discover relationships.
        </p>
      </div>
    );
  }

  return (
    <div className="p-3">
      <h4 className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
        Relationships ({entityRelationships.length})
      </h4>
      <div className="space-y-2">
        {entityRelationships.map((rel) => (
          <div
            key={rel.id}
            className="bg-nexus-bg rounded border border-nexus-border p-2"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-mono text-nexus-cyan">{rel.type}</span>
              <span className="text-[10px] text-nexus-text-secondary">{rel.sourceInt}</span>
            </div>
            <div className="text-[11px] text-nexus-text mb-1">
              {rel.sourceId === entityId ? `-> ${rel.targetId}` : `<- ${rel.sourceId}`}
            </div>
            <ConfidenceBar value={rel.confidence} />
          </div>
        ))}
      </div>
    </div>
  );
}
