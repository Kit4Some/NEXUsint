import { Card } from '@/components/common/Card';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';

const OIL_KEYS = ['WTI Crude', 'Brent Crude'] as const;

export function OilPricesWidget() {
  const oil = useLiveFeedStore((s) => s.oil);
  const hasData = Object.keys(oil).length > 0;

  return (
    <Card className="p-4">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-3">
        Energy Commodities
      </p>

      {hasData ? (
        <div className="space-y-3">
          {OIL_KEYS.map((key) => {
            const data = oil[key];
            if (!data) return null;

            const changeColor = data.up ? 'text-emerald-400' : 'text-red-400';
            const arrow = data.up ? '▲' : '▼';
            const sign = data.up ? '+' : '';

            return (
              <div
                key={key}
                className="flex items-center justify-between py-2 px-3 rounded-md bg-nexus-surface/50 border border-nexus-border/20"
              >
                <div>
                  <p className="text-xs font-mono text-nexus-text-primary font-bold">
                    {data.name}
                  </p>
                  <p className="text-[10px] font-mono text-nexus-text-secondary mt-0.5">
                    USD/barrel
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-mono text-nexus-text-primary font-bold tabular-nums">
                    ${data.price.toFixed(2)}
                  </p>
                  <p className={`text-[11px] font-mono tabular-nums ${changeColor}`}>
                    <span className="text-[9px]">{arrow}</span> {sign}
                    {data.change_percent.toFixed(2)}%
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-4">
          <span className="text-nexus-text-secondary/40 text-lg">--</span>
          <p className="text-[10px] font-mono text-nexus-text-secondary/50 mt-1 italic">
            Awaiting commodity data feed
          </p>
        </div>
      )}
    </Card>
  );
}
