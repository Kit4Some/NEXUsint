import type { ExecutiveSummaryData } from '@nexus/shared-types';

interface Props {
  data: ExecutiveSummaryData;
}

export function ExecutiveSummary({ data }: Props) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-heading text-nexus-accent uppercase tracking-wide">Executive Summary</h3>
      <p className="text-sm text-nexus-text-primary leading-relaxed">{data.summary}</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Entities" value={data.entity_count} />
        <MetricCard label="Relationships" value={data.relationship_count} />
        <MetricCard label="Avg Confidence" value={`${(data.average_confidence * 100).toFixed(1)}%`} />
        <MetricCard label="High Risk" value={data.high_risk_entity_count} accent="red" />
      </div>

      {data.entity_type_breakdown && (
        <div className="flex flex-wrap gap-2 mt-2">
          {Object.entries(data.entity_type_breakdown).map(([type, count]) => (
            <span key={type} className="px-2 py-0.5 text-xs rounded bg-nexus-surface border border-nexus-border text-nexus-text-secondary">
              {type}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="bg-nexus-surface border border-nexus-border rounded-lg p-3 text-center">
      <div className={`text-xl font-bold ${accent === 'red' ? 'text-red-400' : 'text-nexus-accent'}`}>
        {value}
      </div>
      <div className="text-xs text-nexus-text-secondary uppercase tracking-wide mt-1">{label}</div>
    </div>
  );
}
