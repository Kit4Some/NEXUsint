import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { Card } from '@/components/common/Card';
import { useDashboardStats } from '@/hooks/useDashboard';

const INT_COLORS: Record<string, string> = {
  CYBINT: '#FF3366',
  SOCMINT: '#3B82F6',
  SIGINT: '#FFB800',
  GEOINT: '#00FF88',
};

const INT_NAMES = ['CYBINT', 'SOCMINT', 'SIGINT', 'GEOINT'];

export function IntCoverageWidget() {
  const { data } = useDashboardStats();
  const coverage = data?.int_coverage || {};

  const INT_DATA = INT_NAMES.map((name) => ({
    name,
    value: coverage[name] || 0,
    color: INT_COLORS[name] || '#2A3154',
  }));

  const total = INT_DATA.reduce((sum, d) => sum + d.value, 0);

  return (
    <Card className="p-4">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
        INT Coverage
      </p>
      <div className="flex items-center gap-3">
        <div className="w-16 h-16">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={total > 0 ? INT_DATA : [{ name: 'Empty', value: 1, color: '#2A3154' }]}
                cx="50%"
                cy="50%"
                innerRadius={18}
                outerRadius={30}
                dataKey="value"
                strokeWidth={0}
              >
                {(total > 0 ? INT_DATA : [{ name: 'Empty', value: 1, color: '#2A3154' }]).map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-1">
          {INT_DATA.map((d) => (
            <div key={d.name} className="flex items-center gap-1.5 text-[10px]">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
              <span className="text-nexus-text-secondary">{d.name}</span>
              <span className="text-nexus-text font-mono ml-auto">{d.value}</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
