interface OverviewTabProps {
  entity: {
    id: string;
    type: string;
    name: string;
    properties: Record<string, unknown>;
    confidence: number;
    sourceInt: string;
    riskScore: number;
    firstSeen: string;
    lastSeen: string;
  };
}

export function OverviewTab({ entity }: OverviewTabProps) {
  const properties = Object.entries(entity.properties);

  return (
    <div className="p-3 space-y-4">
      {/* Properties Table */}
      <div>
        <h4 className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
          Properties
        </h4>
        <div className="space-y-1">
          <PropertyRow label="ID" value={entity.id} />
          <PropertyRow label="Type" value={entity.type} />
          <PropertyRow label="Name" value={entity.name} />
          <PropertyRow label="Source INT" value={entity.sourceInt} />
          {entity.firstSeen && <PropertyRow label="First Seen" value={entity.firstSeen} />}
          {entity.lastSeen && <PropertyRow label="Last Seen" value={entity.lastSeen} />}
          {properties.map(([key, value]) => (
            <PropertyRow key={key} label={key} value={String(value)} />
          ))}
        </div>
      </div>

      {/* Intelligence Summary Placeholder */}
      <div>
        <h4 className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
          Intelligence Summary
        </h4>
        <div className="bg-nexus-bg rounded border border-nexus-border p-2 text-xs text-nexus-text-secondary italic">
          AI-generated intelligence summary will appear here after investigation analysis.
        </div>
      </div>

      {/* Source Provenance */}
      <div>
        <h4 className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
          Source Provenance
        </h4>
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <div className="w-1.5 h-1.5 rounded-full bg-nexus-cyan" />
            <span className="text-nexus-text">{entity.sourceInt}</span>
            <span className="text-nexus-text-secondary ml-auto">
              conf: {entity.confidence.toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function PropertyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="text-nexus-text-secondary w-24 shrink-0 font-mono">{label}</span>
      <span className="text-nexus-text break-all">{value}</span>
    </div>
  );
}
