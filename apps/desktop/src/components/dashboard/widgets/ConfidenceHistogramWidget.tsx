import { Card } from '@/components/common/Card';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useDashboardStats } from '@/hooks/useDashboard';

const EMPTY_DATA = [
  { bucket: '0-0.2', count: 0 },
  { bucket: '0.2-0.4', count: 0 },
  { bucket: '0.4-0.6', count: 0 },
  { bucket: '0.6-0.8', count: 0 },
  { bucket: '0.8-1.0', count: 0 },
];

export function ConfidenceHistogramWidget() {
  const { data: stats } = useDashboardStats();
  const data = stats?.confidence_distribution?.length ? stats.confidence_distribution : EMPTY_DATA;
  return (
    <Card className="p-4">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-3">
        Confidence Distribution
      </p>

      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={data}>
          <XAxis
            dataKey="bucket"
            tick={{ fontSize: 9, fill: '#8b95b0' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis hide />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1f36',
              border: '1px solid #2a3154',
              borderRadius: 8,
              fontSize: 10,
              fontFamily: 'monospace',
            }}
            labelStyle={{ color: '#c0c0c0' }}
          />
          <Bar dataKey="count" fill="#00d4ff" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
