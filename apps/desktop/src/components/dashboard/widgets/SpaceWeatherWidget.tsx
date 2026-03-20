import { Card } from '@/components/common/Card';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';

function getKpColor(kp: number): string {
  if (kp <= 3) return 'text-emerald-400';
  if (kp <= 4) return 'text-yellow-400';
  return 'text-red-400';
}

function getKpBgColor(kp: number): string {
  if (kp <= 3) return 'bg-emerald-500/20 border-emerald-500/30';
  if (kp <= 4) return 'bg-yellow-500/20 border-yellow-500/30';
  return 'bg-red-500/20 border-red-500/30';
}

function getKpLabel(kp: number): string {
  if (kp <= 1) return 'QUIET';
  if (kp <= 3) return 'UNSETTLED';
  if (kp <= 4) return 'ACTIVE';
  return 'STORM';
}

export function SpaceWeatherWidget() {
  const spaceWeather = useLiveFeedStore((s) => s.spaceWeather);

  if (!spaceWeather) {
    return (
      <Card className="p-4">
        <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-3">
          Space Weather
        </p>
        <div className="flex flex-col items-center justify-center py-4">
          <span className="text-nexus-text-secondary/40 text-lg">--</span>
          <p className="text-[10px] font-mono text-nexus-text-secondary/50 mt-1 italic">
            Awaiting space weather data
          </p>
        </div>
      </Card>
    );
  }

  const kp = spaceWeather.kp_index;
  const kpText = spaceWeather.kp_text || getKpLabel(kp);
  const kpColor = getKpColor(kp);
  const kpBg = getKpBgColor(kp);
  const recentEvents = (spaceWeather.events || []).slice(0, 5);

  return (
    <Card className="p-4">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-3">
        Space Weather
      </p>

      <div className="flex items-center gap-3 mb-3">
        <div
          className={`flex items-center justify-center w-14 h-14 rounded-lg border ${kpBg}`}
        >
          <span className={`text-2xl font-heading font-bold tabular-nums ${kpColor}`}>
            {kp}
          </span>
        </div>
        <div>
          <p className={`text-sm font-mono font-bold ${kpColor}`}>{kpText}</p>
          <p className="text-[10px] font-mono text-nexus-text-secondary mt-0.5">
            Kp Index (Planetary)
          </p>
        </div>
      </div>

      {recentEvents.length > 0 && (
        <div>
          <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-1.5">
            Recent Events
          </p>
          <div className="space-y-1 max-h-28 overflow-y-auto">
            {recentEvents.map((event, i) => (
              <div
                key={i}
                className="text-[10px] font-mono text-nexus-text-secondary py-1 px-2 rounded bg-nexus-surface/30 border border-nexus-border/10"
              >
                {String(event.type || event.message || JSON.stringify(event))}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
