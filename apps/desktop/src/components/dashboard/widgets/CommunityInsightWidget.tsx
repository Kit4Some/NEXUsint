import { useCommunityInsights } from '@/hooks/useAnalytics';
import { Card } from '@/components/common/Card';

interface Community {
  community_id: number;
  member_count: number;
  int_composition: Record<string, number>;
  average_confidence: number;
  average_risk: number;
  max_risk: number;
  risk_level: string;
}

const RISK_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-900/30',
  high: 'text-orange-400 bg-orange-900/30',
  medium: 'text-yellow-400 bg-yellow-900/30',
  low: 'text-green-400 bg-green-900/30',
};

const INT_COLORS: Record<string, string> = {
  CYBINT: 'bg-red-500',
  SOCMINT: 'bg-blue-500',
  SIGINT: 'bg-purple-500',
  GEOINT: 'bg-green-500',
};

export function CommunityInsightWidget() {
  const { data, isLoading } = useCommunityInsights();
  const communities = ((data as { communities?: Community[] })?.communities ?? []).slice(0, 6);

  return (
    <Card className="p-3">
      <h3 className="text-xs font-mono uppercase tracking-wider text-nexus-text-secondary mb-3">
        Community Insights
      </h3>

      {isLoading ? (
        <div className="flex items-center justify-center h-24">
          <div className="w-5 h-5 border-2 border-nexus-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : communities.length === 0 ? (
        <p className="text-xs text-nexus-text-secondary text-center py-4">No communities detected</p>
      ) : (
        <div className="space-y-2">
          {communities.map((c) => (
            <div
              key={c.community_id}
              className="px-2.5 py-2 bg-nexus-bg/50 rounded border border-nexus-border"
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-nexus-text-primary font-medium">
                  Community {c.community_id}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-nexus-text-secondary">
                    {c.member_count} members
                  </span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${RISK_COLORS[c.risk_level] || RISK_COLORS.low}`}>
                    {c.risk_level}
                  </span>
                </div>
              </div>

              {/* INT composition bar */}
              <div className="flex h-2 rounded-full overflow-hidden bg-nexus-border/30">
                {Object.entries(c.int_composition).map(([intType, count]) => {
                  const pct = (count / c.member_count) * 100;
                  return (
                    <div
                      key={intType}
                      className={`${INT_COLORS[intType] || 'bg-gray-500'}`}
                      style={{ width: `${pct}%` }}
                      title={`${intType}: ${count} (${pct.toFixed(0)}%)`}
                    />
                  );
                })}
              </div>

              <div className="flex justify-between mt-1">
                <span className="text-[10px] text-nexus-text-secondary">
                  Conf: {(c.average_confidence * 100).toFixed(0)}%
                </span>
                <span className="text-[10px] text-nexus-text-secondary">
                  Risk: {c.average_risk.toFixed(1)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
