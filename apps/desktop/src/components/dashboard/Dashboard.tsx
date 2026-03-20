import { useState, useRef, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { IntCoverageWidget } from './widgets/IntCoverageWidget';
import { LiveFeedWidget } from './widgets/LiveFeedWidget';
import { ThreatGaugeWidget } from './widgets/ThreatGaugeWidget';
import { EntityTimelineWidget } from './widgets/EntityTimelineWidget';
import { CrossIntMatrixWidget } from './widgets/CrossIntMatrixWidget';
import { ConfidenceHistogramWidget } from './widgets/ConfidenceHistogramWidget';
import { ActiveCollectionsWidget } from './widgets/ActiveCollectionsWidget';
import { AnomalyWidget } from './widgets/AnomalyWidget';
import { CommunityInsightWidget } from './widgets/CommunityInsightWidget';
import { LiveFeedStatusWidget } from './widgets/LiveFeedStatusWidget';
import { DefenseStocksWidget } from './widgets/DefenseStocksWidget';
import { OilPricesWidget } from './widgets/OilPricesWidget';
import { SpaceWeatherWidget } from './widgets/SpaceWeatherWidget';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { seed } from '@/services/api';
import { useDashboardStats } from '@/hooks/useDashboard';

function SeedBanner() {
  const { data: stats, isError, error } = useDashboardStats();
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const autoTriggered = useRef(false);

  const entityCount = stats?.total_entities ?? 0;

  // Auto-seed when DB is empty and stats loaded successfully
  useEffect(() => {
    if (entityCount === 0 && stats && !autoTriggered.current && !result && !loading) {
      autoTriggered.current = true;
      const timer = setTimeout(() => {
        handleSeed();
      }, 2000);
      return () => clearTimeout(timer);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityCount, stats]);

  if (entityCount > 0 && !result) return null;

  const handleSeed = async () => {
    setLoading(true);
    try {
      const res = await seed.demo();
      const msg = res.status === 'already_seeded'
        ? `Already loaded: ${res.entities} entities, ${res.relationships} relationships`
        : `Loaded ${res.entities} entities, ${res.relationships} relationships`;
      setResult(msg);
      // Invalidate all queries so widgets refresh with new data
      queryClient.invalidateQueries();
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Failed to seed data';
      setResult(`Error: ${errMsg}. Check that API server is running on localhost:8000.`);
      console.error('[Dashboard] Seed failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mb-4 p-4 rounded-lg glass-panel premium-border text-center">
      {isError && !result && (
        <div className="mb-3">
          <p className="text-sm text-red-400 font-mono">
            API connection failed: {error instanceof Error ? error.message : 'Network error'}
          </p>
          <p className="text-[10px] text-nexus-text-secondary mt-1">
            Ensure API server is running: uvicorn nexus.main:app --host 0.0.0.0 --port 8000
          </p>
        </div>
      )}
      {result ? (
        <p className={`text-sm font-mono ${result.startsWith('Error') ? 'text-red-400' : 'text-nexus-cyan'}`}>{result}</p>
      ) : (
        <>
          <p className="text-sm text-nexus-text-secondary mb-3">
            {loading ? 'Auto-loading demo OSINT data...' : 'No entities in the knowledge graph. Load demo OSINT data to explore all views.'}
          </p>
          <button
            onClick={handleSeed}
            disabled={loading}
            className="px-6 py-2 text-xs font-mono uppercase tracking-wider bg-nexus-cyan/20 text-nexus-cyan rounded border border-nexus-cyan/30 hover:bg-nexus-cyan/30 transition-colors disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Load Demo Data'}
          </button>
        </>
      )}
    </div>
  );
}

export function Dashboard() {
  return (
    <div className="h-full overflow-y-auto p-4">
      <h2 className="text-lg font-heading font-bold text-nexus-text mb-4">
        Intelligence Dashboard
      </h2>

      <SeedBanner />

      {/* Top Row — Key Metrics */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <ErrorBoundary><ThreatGaugeWidget /></ErrorBoundary>
        <ErrorBoundary><IntCoverageWidget /></ErrorBoundary>
        <ErrorBoundary><ActiveCollectionsWidget /></ErrorBoundary>
      </div>

      {/* Middle Row */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <ErrorBoundary><CrossIntMatrixWidget /></ErrorBoundary>
        <ErrorBoundary><ConfidenceHistogramWidget /></ErrorBoundary>
      </div>

      {/* Analytics Row */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <ErrorBoundary><AnomalyWidget /></ErrorBoundary>
        <ErrorBoundary><CommunityInsightWidget /></ErrorBoundary>
      </div>

      {/* Live Feed Row */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <ErrorBoundary><LiveFeedStatusWidget /></ErrorBoundary>
        <ErrorBoundary><DefenseStocksWidget /></ErrorBoundary>
        <ErrorBoundary><OilPricesWidget /></ErrorBoundary>
      </div>

      {/* Space Weather + Live Intelligence */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <ErrorBoundary><SpaceWeatherWidget /></ErrorBoundary>
        <ErrorBoundary><LiveFeedWidget /></ErrorBoundary>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 gap-3">
        <ErrorBoundary><EntityTimelineWidget /></ErrorBoundary>
      </div>
    </div>
  );
}
