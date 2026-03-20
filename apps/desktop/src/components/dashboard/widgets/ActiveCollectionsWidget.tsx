import { Card } from '@/components/common/Card';
import { useDashboardStats } from '@/hooks/useDashboard';

const INT_BADGES: Record<string, string> = {
  CYBINT: 'bg-red-500/20 text-red-400',
  SOCMINT: 'bg-purple-500/20 text-purple-400',
  SIGINT: 'bg-orange-500/20 text-orange-400',
  GEOINT: 'bg-green-500/20 text-green-400',
};

export function ActiveCollectionsWidget() {
  const { data } = useDashboardStats();
  const running = data?.active_collections || [];

  return (
    <Card className="p-4">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
        Active Collections
      </p>

      {running.length > 0 ? (
        <div className="space-y-2">
          {running.map((job) => (
            <div key={job.id} className="space-y-1">
              <div className="flex items-center gap-2">
                <span
                  className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                    INT_BADGES[job.int_type] || 'bg-gray-500/20 text-gray-400'
                  }`}
                >
                  {job.int_type}
                </span>
                <span className="text-xs font-mono text-nexus-text-primary truncate">
                  {job.query}
                </span>
              </div>
              <div className="w-full h-1 bg-nexus-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-nexus-cyan transition-all rounded-full"
                  style={{ width: `${job.progress}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-nexus-text-secondary">
                <span>{job.scan_type}</span>
                <span>{job.progress}%</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-end gap-2">
          <span className="text-2xl font-heading font-bold text-nexus-cyan">0</span>
          <span className="text-xs text-nexus-text-secondary mb-0.5">running</span>
        </div>
      )}
    </Card>
  );
}
