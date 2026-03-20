import type { EntityAnalysisData } from '@nexus/shared-types';

interface Props {
  data: EntityAnalysisData;
}

export function EntityBreakdown({ data }: Props) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-heading text-nexus-accent uppercase tracking-wide">
        Entity Analysis ({data.total_types} types)
      </h3>

      {Object.entries(data.groups).map(([type, entities]) => (
        <div key={type} className="bg-nexus-surface border border-nexus-border rounded-lg overflow-hidden">
          <div className="px-3 py-2 bg-nexus-border/30 text-sm font-medium text-nexus-text-primary">
            {type} ({entities.length})
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-nexus-text-secondary border-b border-nexus-border">
                <th className="text-left px-3 py-1.5">Name</th>
                <th className="text-left px-3 py-1.5">Confidence</th>
                <th className="text-left px-3 py-1.5">Risk</th>
                <th className="text-left px-3 py-1.5">Source</th>
                <th className="text-left px-3 py-1.5">Grade</th>
              </tr>
            </thead>
            <tbody>
              {entities.slice(0, 20).map((entity) => (
                <tr key={entity.id} className="border-b border-nexus-border/50 hover:bg-nexus-border/20">
                  <td className="px-3 py-1.5 text-nexus-text-primary">{entity.name}</td>
                  <td className="px-3 py-1.5">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-nexus-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-nexus-accent rounded-full"
                          style={{ width: `${entity.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-nexus-text-secondary">{(entity.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className={`px-3 py-1.5 font-medium ${riskColor(entity.risk_score)}`}>
                    {entity.risk_score.toFixed(1)}
                  </td>
                  <td className="px-3 py-1.5 text-nexus-text-secondary">{entity.source_int}</td>
                  <td className="px-3 py-1.5">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${gradeColor(entity.reliability_grade)}`}>
                      {entity.reliability_grade}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function riskColor(score: number): string {
  if (score >= 9) return 'text-red-400';
  if (score >= 7) return 'text-orange-400';
  if (score >= 4) return 'text-yellow-400';
  return 'text-green-400';
}

function gradeColor(grade: string): string {
  switch (grade) {
    case 'A': return 'bg-green-900/40 text-green-400';
    case 'B': return 'bg-blue-900/40 text-blue-400';
    case 'C': return 'bg-yellow-900/40 text-yellow-400';
    case 'D': return 'bg-orange-900/40 text-orange-400';
    default: return 'bg-red-900/40 text-red-400';
  }
}
