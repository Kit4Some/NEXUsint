interface RawDataTabProps {
  entity: Record<string, unknown>;
}

export function RawDataTab({ entity }: RawDataTabProps) {
  return (
    <div className="p-3">
      <h4 className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
        Raw Data
      </h4>
      <pre className="bg-nexus-bg rounded border border-nexus-border p-3 text-[11px] font-mono text-nexus-text overflow-x-auto">
        {JSON.stringify(entity, null, 2)}
      </pre>
    </div>
  );
}
