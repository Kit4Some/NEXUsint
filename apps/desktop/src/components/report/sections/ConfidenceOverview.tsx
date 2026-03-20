import type { ConfidenceMetricsData } from '@nexus/shared-types';

interface Props {
  data: ConfidenceMetricsData;
}

const GRADE_CONFIG: Record<string, { label: string; color: string }> = {
  A: { label: 'Completely Reliable', color: 'bg-green-500' },
  B: { label: 'Usually Reliable', color: 'bg-blue-500' },
  C: { label: 'Fairly Reliable', color: 'bg-yellow-500' },
  D: { label: 'Not Usually Reliable', color: 'bg-orange-500' },
  E: { label: 'Unreliable', color: 'bg-red-500' },
  F: { label: 'Cannot Be Judged', color: 'bg-gray-500' },
};

export function ConfidenceOverview({ data }: Props) {
  const totalGrades = Object.values(data.admiralty_grade_distribution).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-heading text-nexus-accent uppercase tracking-wide">Confidence Metrics</h3>

      <div className="bg-nexus-surface border border-nexus-border rounded-lg p-4 text-center">
        <div className="text-3xl font-bold text-nexus-accent">
          {(data.overall_average * 100).toFixed(1)}%
        </div>
        <div className="text-xs text-nexus-text-secondary uppercase mt-1">Overall Confidence</div>
      </div>

      {/* Admiralty Grade Distribution */}
      <div>
        <h4 className="text-xs text-nexus-text-secondary mb-2 uppercase tracking-wide">
          Admiralty Reliability Grades
        </h4>
        <div className="space-y-1.5">
          {Object.entries(GRADE_CONFIG).map(([grade, config]) => {
            const count = data.admiralty_grade_distribution[grade] ?? 0;
            const pct = (count / totalGrades) * 100;
            return (
              <div key={grade} className="flex items-center gap-2">
                <span className="w-5 text-xs font-bold text-nexus-text-primary">{grade}</span>
                <div className="flex-1 h-4 bg-nexus-border/30 rounded overflow-hidden">
                  <div
                    className={`h-full ${config.color} rounded transition-all duration-500`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-20 text-xs text-nexus-text-secondary text-right">
                  {count} ({pct.toFixed(0)}%)
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Confidence by INT */}
      {Object.keys(data.confidence_by_int).length > 0 && (
        <div>
          <h4 className="text-xs text-nexus-text-secondary mb-2 uppercase tracking-wide">
            Confidence by INT Source
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.confidence_by_int).map(([source, avg]) => (
              <div key={source} className="bg-nexus-surface border border-nexus-border rounded-lg p-3">
                <div className="text-xs text-nexus-text-secondary">{source}</div>
                <div className="text-lg font-bold text-nexus-text-primary mt-1">
                  {(avg * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-nexus-text-secondary">
                  {data.entity_count_by_int[source] ?? 0} entities
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
