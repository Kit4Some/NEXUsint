import { Card } from '@/components/common/Card';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';

export function LiveFeedWidget() {
  const flights = useLiveFeedStore((s) => s.flights);
  const militaryFlights = useLiveFeedStore((s) => s.militaryFlights);
  const trackedFlights = useLiveFeedStore((s) => s.trackedFlights);
  const news = useLiveFeedStore((s) => s.news);
  const earthquakes = useLiveFeedStore((s) => s.earthquakes);
  const fires = useLiveFeedStore((s) => s.fires);
  const isActive = useLiveFeedStore((s) => s.isActive);

  const totalEntities =
    flights.length + militaryFlights.length + trackedFlights.length;

  return (
    <Card className="p-4 flex flex-col max-h-64">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
        Live Intelligence Feed
      </p>
      <div className="flex-1 overflow-y-auto space-y-2">
        {!isActive ? (
          <p className="text-xs text-nexus-text-secondary italic">
            Live feed inactive. Go to Dashboard → Live Feed Status → START to activate.
          </p>
        ) : totalEntities === 0 && news.length === 0 ? (
          <p className="text-xs text-nexus-text-secondary italic">
            Live feed active — waiting for first data cycle (up to 60s)...
          </p>
        ) : (
          <>
            {/* Flight summary */}
            {totalEntities > 0 && (
              <div className="text-[11px] font-mono">
                <span className="text-cyan-400">SIGINT</span>
                <span className="text-nexus-text-secondary ml-2">
                  {flights.length} flights · {militaryFlights.length} military · {trackedFlights.length} tracked
                </span>
              </div>
            )}

            {/* News summary */}
            {news.length > 0 && (
              <div className="space-y-1">
                <div className="text-[11px] font-mono">
                  <span className="text-amber-400">NEWS</span>
                  <span className="text-nexus-text-secondary ml-2">{news.length} articles</span>
                </div>
                {news.slice(0, 5).map((article, i) => (
                  <div key={i} className="flex items-start gap-2 text-[10px] pl-2">
                    <span
                      className={`shrink-0 font-bold ${
                        article.risk_score >= 8
                          ? 'text-red-400'
                          : article.risk_score >= 6
                            ? 'text-orange-400'
                            : article.risk_score >= 4
                              ? 'text-yellow-400'
                              : 'text-green-400'
                      }`}
                    >
                      [{article.risk_score}]
                    </span>
                    <span className="text-nexus-text truncate">{article.title}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Earthquakes */}
            {earthquakes.length > 0 && (
              <div className="text-[11px] font-mono">
                <span className="text-yellow-400">GEOINT</span>
                <span className="text-nexus-text-secondary ml-2">{earthquakes.length} earthquakes</span>
              </div>
            )}

            {/* Fires */}
            {fires.length > 0 && (
              <div className="text-[11px] font-mono">
                <span className="text-orange-400">FIRMS</span>
                <span className="text-nexus-text-secondary ml-2">{fires.length} fire hotspots</span>
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );
}
