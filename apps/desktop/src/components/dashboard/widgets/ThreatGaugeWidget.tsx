import { Card } from '@/components/common/Card';
import { PieChart, Pie, Cell } from 'recharts';
import { useDashboardStats } from '@/hooks/useDashboard';

const LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const;
const LEVEL_COLORS: Record<string, string> = {
  LOW: '#22c55e',
  MEDIUM: '#f59e0b',
  HIGH: '#ef4444',
  CRITICAL: '#dc2626',
};

export function ThreatGaugeWidget() {
  const { data } = useDashboardStats();
  const level = (data?.threat_level || 'LOW') as typeof LEVELS[number];
  const score = data?.threat_score ?? 0;
  const gaugeData = [
    { value: score },
    { value: 100 - score },
  ];

  const color = LEVEL_COLORS[level];

  return (
    <Card className="p-4">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
        Threat Level
      </p>

      <div className="flex items-center gap-3">
        <div className="relative">
          <PieChart width={80} height={50}>
            <Pie
              data={gaugeData}
              cx={40}
              cy={45}
              startAngle={180}
              endAngle={0}
              innerRadius={25}
              outerRadius={35}
              dataKey="value"
              stroke="none"
            >
              <Cell fill={color} />
              <Cell fill="rgba(42,49,84,0.5)" />
            </Pie>
          </PieChart>
          <div className="absolute inset-0 flex items-end justify-center pb-1">
            <span className="text-[10px] font-mono" style={{ color }}>{score}</span>
          </div>
        </div>

        <div>
          <span className="text-lg font-heading font-bold" style={{ color }}>
            {level}
          </span>
          <p className="text-[10px] font-mono text-nexus-text-secondary mt-0.5">
            Based on entity risk scores
          </p>
        </div>
      </div>
    </Card>
  );
}
