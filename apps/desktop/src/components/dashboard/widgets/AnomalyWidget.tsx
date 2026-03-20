import { useAnomalyDetection } from '@/hooks/useAnalytics';
import { Card } from '@/components/common/Card';

const ANOMALY_ICONS: Record<string, string> = {
  statistical_outlier: 'S',
  isolation_forest: 'I',
  graph_structural: 'G',
  bridge_entity: 'B',
  temporal_spike: 'T',
};

const ANOMALY_COLORS: Record<string, string> = {
  statistical_outlier: 'text-purple-400 border-purple-700',
  isolation_forest: 'text-violet-400 border-violet-700',
  graph_structural: 'text-blue-400 border-blue-700',
  bridge_entity: 'text-cyan-400 border-cyan-700',
  temporal_spike: 'text-amber-400 border-amber-700',
};

interface AnomalyItem {
  entity_id: string;
  entity_name: string;
  anomaly_type: string;
  score: number;
  evidence: Record<string, unknown>;
}

export function AnomalyWidget() {
  const { data, isLoading } = useAnomalyDetection();
  const anomalies = ((data as { anomalies?: AnomalyItem[] })?.anomalies ?? []).slice(0, 8);

  return (
    <Card className="p-3">
      <h3 className="text-xs font-mono uppercase tracking-wider text-nexus-text-secondary mb-3">
        Anomaly Detection
      </h3>

      {isLoading ? (
        <div className="flex items-center justify-center h-24">
          <div className="w-5 h-5 border-2 border-nexus-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : anomalies.length === 0 ? (
        <p className="text-xs text-nexus-text-secondary text-center py-4">No anomalies detected</p>
      ) : (
        <div className="space-y-2">
          {anomalies.map((a, i) => (
            <div
              key={`${a.entity_id}-${a.anomaly_type}-${i}`}
              className="flex items-center gap-2 px-2 py-1.5 bg-nexus-bg/50 rounded border border-nexus-border hover:border-nexus-accent/50 transition-colors"
            >
              <span className={`flex-shrink-0 w-6 h-6 flex items-center justify-center text-xs font-bold rounded border ${ANOMALY_COLORS[a.anomaly_type] || 'text-gray-400 border-gray-700'}`}>
                {ANOMALY_ICONS[a.anomaly_type] || '?'}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-nexus-text-primary truncate">{a.entity_name}</p>
                <p className="text-[10px] text-nexus-text-secondary">
                  {a.anomaly_type.replace(/_/g, ' ')}
                </p>
              </div>
              <div className="flex-shrink-0">
                <SeverityBar score={a.score} />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function SeverityBar({ score }: { score: number }) {
  const normalizedScore = Math.min(1, Math.max(0, score / 5)); // normalize to 0-1
  const color = normalizedScore > 0.7 ? 'bg-red-500' : normalizedScore > 0.4 ? 'bg-amber-500' : 'bg-blue-500';

  return (
    <div className="flex items-center gap-1">
      <div className="w-12 h-1.5 bg-nexus-border rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${normalizedScore * 100}%` }} />
      </div>
      <span className="text-[10px] text-nexus-text-secondary w-8 text-right">{score.toFixed(1)}</span>
    </div>
  );
}
