import type { RiskAssessmentData } from '@nexus/shared-types';

interface Props {
  data: RiskAssessmentData;
}

const RISK_LEVELS = [
  { key: 'critical', label: 'Critical', color: 'bg-red-500' },
  { key: 'high', label: 'High', color: 'bg-orange-500' },
  { key: 'medium', label: 'Medium', color: 'bg-yellow-500' },
  { key: 'low', label: 'Low', color: 'bg-green-500' },
] as const;

export function RiskMatrix({ data }: Props) {
  const total = Object.values(data.risk_distribution).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-heading text-nexus-accent uppercase tracking-wide">Risk Assessment</h3>

      {/* Risk distribution bars */}
      <div className="space-y-2">
        {RISK_LEVELS.map(({ key, label, color }) => {
          const count = data.risk_distribution[key] ?? 0;
          const pct = (count / total) * 100;
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="w-16 text-xs text-nexus-text-secondary">{label}</span>
              <div className="flex-1 h-5 bg-nexus-border/30 rounded overflow-hidden">
                <div
                  className={`h-full ${color} rounded transition-all duration-500`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-12 text-xs text-nexus-text-secondary text-right">{count} ({pct.toFixed(0)}%)</span>
            </div>
          );
        })}
      </div>

      {/* Critical entities */}
      {data.critical_entities.length > 0 && (
        <div>
          <h4 className="text-xs text-red-400 font-medium mb-2 uppercase">Critical Entities</h4>
          <div className="space-y-1">
            {data.critical_entities.map((e) => (
              <div key={e.id} className="flex items-center justify-between px-3 py-1.5 bg-red-900/20 border border-red-900/40 rounded text-xs">
                <span className="text-nexus-text-primary">{e.name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-nexus-text-secondary">{e.type}</span>
                  <span className="text-red-400 font-medium">{e.risk_score.toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* High risk entities */}
      {data.high_risk_entities.length > 0 && (
        <div>
          <h4 className="text-xs text-orange-400 font-medium mb-2 uppercase">High Risk Entities</h4>
          <div className="space-y-1">
            {data.high_risk_entities.map((e) => (
              <div key={e.id} className="flex items-center justify-between px-3 py-1.5 bg-orange-900/20 border border-orange-900/40 rounded text-xs">
                <span className="text-nexus-text-primary">{e.name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-nexus-text-secondary">{e.type}</span>
                  <span className="text-orange-400 font-medium">{e.risk_score.toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
