import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCollectionStore, type IntType, type HistoryJob } from '@/stores/useCollectionStore';
import { useStartCollection, useJobPoller, getScanTypes } from '@/hooks/useCollection';
import { useMapStore } from '@/stores/useMapStore';
import { monitoring, collection as collectionApi } from '@/services/api';

const INT_OPTIONS: { id: IntType; label: string; color: string }[] = [
  { id: 'cybint', label: 'CYBINT', color: 'text-red-400' },
  { id: 'socmint', label: 'SOCMINT', color: 'text-blue-400' },
  { id: 'sigint', label: 'SIGINT', color: 'text-amber-400' },
  { id: 'geoint', label: 'GEOINT', color: 'text-emerald-400' },
];

function JobProgress({ status, progress }: { status: string; progress: number }) {
  const colors: Record<string, string> = {
    queued: 'bg-gray-400',
    running: 'bg-nexus-cyan',
    completed: 'bg-green-400',
    failed: 'bg-red-400',
  };
  return (
    <div className="w-full h-1.5 bg-nexus-bg rounded-full overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${colors[status] || 'bg-gray-400'}`}
        initial={{ width: 0 }}
        animate={{ width: `${Math.max(progress, status === 'queued' ? 5 : 0)}%` }}
        transition={{ duration: 0.5 }}
      />
    </div>
  );
}

const INT_COLORS: Record<string, string> = {
  CYBINT: 'text-red-400',
  SOCMINT: 'text-blue-400',
  SIGINT: 'text-amber-400',
  GEOINT: 'text-emerald-400',
};

const STATUS_COLORS: Record<string, string> = {
  completed: 'text-green-400',
  failed: 'text-red-400',
  running: 'text-nexus-cyan',
  queued: 'text-gray-400',
};

function HistoryTab() {
  const { historyJobs, historyTotal, setHistoryJobs, selectedJobEntities, setSelectedJobEntities } = useCollectionStore();
  const [loading, setLoading] = useState(false);
  const [expandedJob, setExpandedJob] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await collectionApi.getHistory({ limit: 50 });
      setHistoryJobs(data.jobs, data.total);
    } catch { /* API unavailable */ }
    setLoading(false);
  }, [setHistoryJobs]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const handleExpandJob = async (job: HistoryJob) => {
    if (expandedJob === job.id) {
      setExpandedJob(null);
      setSelectedJobEntities([]);
      return;
    }
    setExpandedJob(job.id);
    try {
      const entities = await collectionApi.getJobEntities(job.id);
      setSelectedJobEntities(entities);
    } catch {
      setSelectedJobEntities([]);
    }
  };

  const formatTime = (iso: string | null) => {
    if (!iso) return '-';
    const d = new Date(iso);
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  };

  return (
    <div className="flex-1 overflow-y-auto px-2 py-1">
      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary">
          {historyTotal} Jobs
        </p>
        <button onClick={fetchHistory} disabled={loading} className="text-[9px] font-mono text-nexus-cyan hover:text-nexus-cyan/80">
          {loading ? '...' : 'Refresh'}
        </button>
      </div>
      {historyJobs.length === 0 ? (
        <p className="text-[10px] text-nexus-text-secondary/50 italic">No collection history yet.</p>
      ) : (
        <div className="space-y-1">
          {historyJobs.map((job) => (
            <div key={job.id}>
              <button
                onClick={() => handleExpandJob(job)}
                className={`w-full text-left p-1.5 rounded border transition-colors ${
                  expandedJob === job.id
                    ? 'bg-nexus-cyan/5 border-nexus-cyan/30'
                    : 'bg-nexus-bg/50 border-nexus-border hover:border-nexus-text-secondary/30'
                }`}
              >
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className={`text-[8px] font-mono font-bold ${INT_COLORS[job.int_type] || 'text-gray-400'}`}>
                    {job.int_type}
                  </span>
                  <span className="text-[9px] font-mono text-nexus-text truncate flex-1">{job.query}</span>
                  <span className={`text-[8px] font-mono ${STATUS_COLORS[job.status] || 'text-gray-400'}`}>
                    {job.status}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[8px] font-mono text-nexus-text-secondary">{job.scan_type}</span>
                  <span className="text-[8px] font-mono text-nexus-text-secondary">
                    {job.result_count} results | {formatTime(job.created_at)}
                  </span>
                </div>
              </button>
              {expandedJob === job.id && (
                <div className="ml-2 mt-1 mb-1 pl-2 border-l border-nexus-cyan/20">
                  {selectedJobEntities.length === 0 ? (
                    <p className="text-[9px] text-nexus-text-secondary/50 italic py-1">No entities recorded.</p>
                  ) : (
                    <div className="space-y-0.5">
                      {selectedJobEntities.slice(0, 15).map((e) => (
                        <div key={e.id} className="flex items-center gap-1.5 py-0.5">
                          <span className="text-[8px] font-mono text-nexus-cyan">{e.type}</span>
                          <span className="text-[9px] font-mono text-nexus-text truncate">{e.name}</span>
                          <span className="text-[7px] font-mono text-nexus-text-secondary ml-auto">
                            {(e.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                      {selectedJobEntities.length > 15 && (
                        <p className="text-[8px] text-nexus-text-secondary">+{selectedJobEntities.length - 15} more</p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function CollectionPanel() {
  const { isOpen, togglePanel, activeJobs, recentEntities, activeTab, setActiveTab } = useCollectionStore();
  const startCollection = useStartCollection();
  useJobPoller();

  const [intType, setIntType] = useState<IntType>('cybint');
  const [query, setQuery] = useState('');
  const [scanType, setScanType] = useState('full');
  const [autoPivot, setAutoPivot] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Live Feed state
  const [liveFeedActive, setLiveFeedActive] = useState(false);
  const [liveFeedLoading, setLiveFeedLoading] = useState(false);
  const [liveFeedInfo, setLiveFeedInfo] = useState<{ aircraft_count: number; timestamp: string } | null>(null);
  const viewState = useMapStore((s) => s.viewState);

  const pollLiveFeedStatus = useCallback(async () => {
    try {
      const status = await monitoring.getLiveFeedStatus();
      setLiveFeedActive(status.active);
      if (status.last_scan) {
        setLiveFeedInfo({ aircraft_count: status.last_scan.aircraft_count, timestamp: status.last_scan.timestamp });
      }
    } catch { /* API unavailable */ }
  }, []);

  useEffect(() => {
    pollLiveFeedStatus();
    const interval = setInterval(pollLiveFeedStatus, 10_000);
    return () => clearInterval(interval);
  }, [pollLiveFeedStatus]);

  const toggleLiveFeed = async () => {
    setLiveFeedLoading(true);
    try {
      if (liveFeedActive) {
        await monitoring.stopLiveFeed();
        setLiveFeedActive(false);
        setLiveFeedInfo(null);
      } else {
        const zoom = viewState.zoom;
        const latRange = 180 / Math.pow(2, zoom);
        const lngRange = 360 / Math.pow(2, zoom);
        await monitoring.startLiveFeed({
          lamin: viewState.latitude - latRange / 2,
          lomin: viewState.longitude - lngRange / 2,
          lamax: viewState.latitude + latRange / 2,
          lomax: viewState.longitude + lngRange / 2,
        });
        setLiveFeedActive(true);
      }
    } catch { /* ignore */ }
    setLiveFeedLoading(false);
  };

  const scanTypes = getScanTypes(intType);

  const handleSubmit = async () => {
    if (!query.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await startCollection(intType, query.trim(), scanType, autoPivot);
      setQuery('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Collection failed');
    } finally {
      setSubmitting(false);
    }
  };

  const jobs = Array.from(activeJobs.values()).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, x: -200 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -200 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="absolute left-12 top-0 bottom-0 w-72 z-30 glass-panel premium-border border-l-0 flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-nexus-border">
            <span className="text-xs font-mono uppercase tracking-wider text-nexus-text">
              OSINT Collection
            </span>
            <button onClick={togglePanel} className="text-nexus-text-secondary hover:text-nexus-text text-sm">
              x
            </button>
          </div>

          {/* Tab Switcher */}
          <div className="flex border-b border-nexus-border">
            <button
              onClick={() => setActiveTab('active')}
              className={`flex-1 text-[10px] font-mono uppercase py-1.5 transition-colors ${
                activeTab === 'active'
                  ? 'text-nexus-cyan border-b-2 border-nexus-cyan'
                  : 'text-nexus-text-secondary hover:text-nexus-text'
              }`}
            >
              Active
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex-1 text-[10px] font-mono uppercase py-1.5 transition-colors ${
                activeTab === 'history'
                  ? 'text-nexus-cyan border-b-2 border-nexus-cyan'
                  : 'text-nexus-text-secondary hover:text-nexus-text'
              }`}
            >
              History
            </button>
          </div>

          {activeTab === 'history' ? <HistoryTab /> : <>

          {/* Live Feed Toggle */}
          <div className="px-2 pt-2">
            <button
              onClick={toggleLiveFeed}
              disabled={liveFeedLoading}
              className={`w-full flex items-center justify-between px-2 py-1.5 text-[10px] font-mono uppercase rounded border transition-colors ${
                liveFeedActive
                  ? 'text-green-400 border-green-500/50 bg-green-500/10'
                  : 'text-nexus-text-secondary border-nexus-border hover:border-nexus-cyan/40'
              }`}
            >
              <span className="flex items-center gap-1.5">
                <span className={`inline-block w-1.5 h-1.5 rounded-full ${liveFeedActive ? 'bg-green-400 animate-pulse' : 'bg-nexus-text-secondary/40'}`} />
                {liveFeedLoading ? 'Processing...' : liveFeedActive ? 'LIVE FEED ACTIVE' : 'START LIVE FEED'}
              </span>
              {liveFeedActive && liveFeedInfo && (
                <span className="text-[8px] text-green-400/70">
                  {liveFeedInfo.aircraft_count} aircraft
                </span>
              )}
            </button>
          </div>

          {/* INT Type Selector */}
          <div className="flex gap-1 px-2 py-2">
            {INT_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                onClick={() => {
                  setIntType(opt.id);
                  setScanType(getScanTypes(opt.id)[0] || 'full');
                }}
                className={`flex-1 text-[9px] font-mono uppercase py-1 rounded border transition-colors ${
                  intType === opt.id
                    ? `${opt.color} border-current bg-white/5`
                    : 'text-nexus-text-secondary border-nexus-border hover:border-nexus-text-secondary'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Query Input */}
          <div className="px-2 space-y-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="Target query (IP, domain, username...)"
              className="w-full px-2 py-1.5 text-xs font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text placeholder:text-nexus-text-secondary/50 focus:border-nexus-cyan/50 focus:outline-none"
            />

            <select
              value={scanType}
              onChange={(e) => setScanType(e.target.value)}
              className="w-full px-2 py-1.5 text-xs font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text focus:border-nexus-cyan/50 focus:outline-none"
            >
              {scanTypes.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>

            {/* Auto-Pivot Toggle */}
            <label className="flex items-center gap-2 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={autoPivot}
                  onChange={(e) => setAutoPivot(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-7 h-4 rounded-full bg-nexus-bg border border-nexus-border peer-checked:bg-nexus-cyan/30 peer-checked:border-nexus-cyan/50 transition-colors" />
                <div className="absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-nexus-text-secondary peer-checked:bg-nexus-cyan peer-checked:translate-x-3 transition-all" />
              </div>
              <span className="text-[10px] font-mono text-nexus-text-secondary group-hover:text-nexus-text transition-colors">
                Auto-Pivot
              </span>
              {autoPivot && (
                <span className="text-[8px] font-mono text-nexus-cyan bg-nexus-cyan/10 px-1 rounded">
                  ON
                </span>
              )}
            </label>

            <button
              onClick={handleSubmit}
              disabled={!query.trim() || submitting}
              className="w-full py-1.5 text-xs font-mono uppercase tracking-wider bg-nexus-cyan/20 text-nexus-cyan rounded border border-nexus-cyan/30 hover:bg-nexus-cyan/30 transition-colors disabled:opacity-40"
            >
              {submitting ? 'Submitting...' : autoPivot ? 'Collect + Pivot' : 'Collect'}
            </button>

            {error && <p className="text-[10px] text-red-400 font-mono">{error}</p>}
          </div>

          {/* Active Jobs */}
          {jobs.length > 0 && (
            <div className="mt-3 px-2">
              <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-1">
                Active Jobs ({jobs.length})
              </p>
              <div className="space-y-1.5 max-h-32 overflow-y-auto">
                {jobs.map((job) => (
                  <div key={job.id} className="p-1.5 rounded bg-nexus-bg/50 border border-nexus-border">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-mono text-nexus-text truncate flex-1">
                        {job.query}
                      </span>
                      <span className="text-[8px] font-mono text-nexus-text-secondary ml-1">
                        {job.status === 'completed' ? `${job.resultCount} results` : `${job.progress}%`}
                      </span>
                    </div>
                    <JobProgress status={job.status} progress={job.progress} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent Discoveries */}
          <div className="mt-3 px-2 flex-1 overflow-y-auto">
            <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-1">
              Discovered Entities ({recentEntities.length})
            </p>
            {recentEntities.length === 0 ? (
              <p className="text-[10px] text-nexus-text-secondary/50 italic">
                Entities will appear here as they are collected...
              </p>
            ) : (
              <div className="space-y-0.5">
                {recentEntities.slice(0, 20).map((entity, i) => (
                  <div key={`${entity.id}-${i}`} className="flex items-center gap-1.5 py-0.5">
                    <span className="text-[8px] font-mono text-nexus-cyan">{entity.type}</span>
                    <span className="text-[10px] font-mono text-nexus-text truncate">{entity.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          </>}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
