import { useState } from 'react';
import { Card } from '@/components/common/Card';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';

function getFreshnessColor(lastUpdated: string): string {
  const ageMs = Date.now() - new Date(lastUpdated).getTime();
  const ageMin = ageMs / 60_000;
  if (ageMin < 2) return 'bg-emerald-400';
  if (ageMin < 5) return 'bg-yellow-400';
  return 'bg-red-400';
}

function getFreshnessLabel(lastUpdated: string): string {
  const ageMs = Date.now() - new Date(lastUpdated).getTime();
  const ageSec = Math.floor(ageMs / 1000);
  if (ageSec < 60) return `${ageSec}s ago`;
  const ageMin = Math.floor(ageSec / 60);
  if (ageMin < 60) return `${ageMin}m ago`;
  return `${Math.floor(ageMin / 60)}h ago`;
}

function formatSourceName(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function LiveFeedStatusWidget() {
  const isActive = useLiveFeedStore((s) => s.isActive);
  const sourceTimestamps = useLiveFeedStore((s) => s.sourceTimestamps);
  const startLiveFeed = useLiveFeedStore((s) => s.startLiveFeed);
  const stopLiveFeed = useLiveFeedStore((s) => s.stopLiveFeed);
  const flights = useLiveFeedStore((s) => s.flights);
  const militaryFlights = useLiveFeedStore((s) => s.militaryFlights);
  const news = useLiveFeedStore((s) => s.news);
  const earthquakes = useLiveFeedStore((s) => s.earthquakes);
  const fires = useLiveFeedStore((s) => s.fires);

  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (isActive) {
        await stopLiveFeed();
      } else {
        await startLiveFeed();
      }
    } catch {
      // Error already logged in store
    } finally {
      setLoading(false);
    }
  };

  const sources = Object.entries(sourceTimestamps);

  const totalEntities =
    flights.length + militaryFlights.length + news.length + earthquakes.length + fires.length;

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary">
          Live Feed Status
        </p>
        <button
          onClick={handleToggle}
          disabled={loading}
          className={`text-[10px] font-mono px-3 py-1 rounded border transition-colors ${
            isActive
              ? 'bg-red-500/20 border-red-500/40 text-red-400 hover:bg-red-500/30'
              : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {loading ? '...' : isActive ? 'STOP' : 'START'}
        </button>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <div
          className={`w-2 h-2 rounded-full ${isActive ? 'bg-emerald-400 animate-pulse' : 'bg-nexus-text-secondary/30'}`}
        />
        <span className="text-xs font-mono text-nexus-text-primary">
          {isActive ? 'Active' : 'Inactive'}
        </span>
        {isActive && (
          <span className="text-[10px] font-mono text-nexus-text-secondary ml-auto tabular-nums">
            {totalEntities} entities
          </span>
        )}
      </div>

      {sources.length > 0 ? (
        <div className="space-y-1.5 max-h-36 overflow-y-auto">
          {sources.map(([source, timestamp]) => (
            <div
              key={source}
              className="flex items-center gap-2 py-1 px-2 rounded bg-nexus-surface/30 border border-nexus-border/10"
            >
              <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${getFreshnessColor(timestamp)}`} />
              <span className="text-[10px] font-mono text-nexus-text-primary flex-1 truncate">
                {formatSourceName(source)}
              </span>
              <span className="text-[10px] font-mono text-nexus-text-secondary tabular-nums shrink-0">
                {getFreshnessLabel(timestamp)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-[10px] font-mono text-nexus-text-secondary/50 text-center italic py-2">
          {isActive ? 'Waiting for source data...' : 'Start feed to see source status'}
        </p>
      )}
    </Card>
  );
}
