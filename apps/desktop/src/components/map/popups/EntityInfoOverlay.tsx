import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMapStore } from '@/stores/useMapStore';
import { useAppStore } from '@/stores/useAppStore';
import { useEntityStore } from '@/stores/useEntityStore';
import { entities as entitiesApi } from '@/services/api';

interface Connection {
  id: string;
  name: string;
  type: string;
  relType: string;
  direction: 'outgoing' | 'incoming';
}

interface OverlayData {
  id: string;
  name: string;
  type: string;
  confidence: number;
  riskScore: number;
  sourceInt: string;
  position?: { latitude: number; longitude: number };
  connections: Connection[];
  lastSeen?: string;
}

const REL_COLORS: Record<string, string> = {
  TARGETS: 'text-red-400',
  COMMUNICATES_WITH: 'text-nexus-cyan',
  HOSTS: 'text-green-400',
  RESOLVES_TO: 'text-blue-400',
  BELONGS_TO: 'text-purple-400',
  ASSOCIATED_WITH: 'text-amber-400',
};

export function EntityInfoOverlay() {
  const { selectedEntityId, activeTracks, addTrackPoints } = useMapStore();
  const { setActiveTab } = useAppStore();
  const { detailPanelOpen, toggleDetailPanel, selectedEntity } = useEntityStore();
  const [data, setData] = useState<OverlayData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedEntityId) { setData(null); return; }
    setLoading(true);
    (async () => {
      try {
        const [entity, graph] = await Promise.all([
          entitiesApi.get(selectedEntityId),
          entitiesApi.getGraph(selectedEntityId, 1),
        ]);
        const e = entity as any;
        const g = graph as any;
        const connections: Connection[] = (g?.edges || g?.relationships || []).slice(0, 10).map((edge: any) => ({
          id: edge.target_id || edge.targetId || edge.id,
          name: edge.target_name || edge.targetName || 'Unknown',
          type: edge.target_type || edge.targetType || 'Entity',
          relType: edge.rel_type || edge.type || 'RELATED_TO',
          direction: edge.source_id === selectedEntityId ? 'outgoing' : 'incoming',
        }));
        setData({
          id: e.id,
          name: e.name,
          type: e.type,
          confidence: e.confidence ?? 0.5,
          riskScore: e.risk_score ?? e.riskScore ?? 0,
          sourceInt: e.source_int || e.sourceInt || 'UNKNOWN',
          position: e.latitude && e.longitude ? { latitude: e.latitude, longitude: e.longitude } : undefined,
          connections,
          lastSeen: e.last_seen || e.lastSeen,
        });
      } catch {
        // Use selectedEntity from store as fallback
        if (selectedEntity) {
          setData({
            id: selectedEntity.id,
            name: selectedEntity.name,
            type: selectedEntity.type,
            confidence: selectedEntity.confidence ?? 0.5,
            riskScore: selectedEntity.riskScore ?? 0,
            sourceInt: selectedEntity.sourceInt || 'UNKNOWN',
            connections: [],
          });
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [selectedEntityId]);

  if (!selectedEntityId || !data) return null;

  const hasTrack = activeTracks.has(selectedEntityId);
  const confidencePct = Math.round(data.confidence * 100);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className="absolute top-16 left-3 z-30 w-72 bg-nexus-card/95 backdrop-blur-sm border border-nexus-border rounded-lg shadow-2xl shadow-black/40 overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-nexus-border bg-nexus-bg/50">
          <span className="text-[10px] font-mono text-nexus-cyan uppercase tracking-wider">Entity Intel</span>
          <button
            onClick={() => useMapStore.getState().setSelectedEntityId(null)}
            className="text-nexus-text-secondary hover:text-nexus-text text-xs"
          >
            X
          </button>
        </div>

        {loading ? (
          <div className="p-4 text-center text-xs text-nexus-text-secondary animate-pulse">Loading intel...</div>
        ) : (
          <div className="p-3 space-y-2.5">
            {/* Name + Type */}
            <div>
              <p className="text-sm font-medium text-nexus-text truncate">{data.name}</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-nexus-cyan/15 text-nexus-cyan">{data.type}</span>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400">{data.sourceInt}</span>
              </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-[9px] text-nexus-text-secondary uppercase">Confidence</span>
                <div className="flex items-center gap-1 mt-0.5">
                  <div className="flex-1 h-1.5 bg-nexus-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-nexus-cyan/60 to-nexus-cyan rounded-full"
                      style={{ width: `${confidencePct}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-mono text-nexus-text">{confidencePct}%</span>
                </div>
              </div>
              <div>
                <span className="text-[9px] text-nexus-text-secondary uppercase">Risk</span>
                <div className="flex items-center gap-1 mt-0.5">
                  <div className="flex-1 h-1.5 bg-nexus-border rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${data.riskScore >= 7 ? 'bg-red-500' : data.riskScore >= 4 ? 'bg-amber-500' : 'bg-green-500'}`}
                      style={{ width: `${data.riskScore * 10}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-mono text-nexus-text">{data.riskScore}/10</span>
                </div>
              </div>
            </div>

            {/* Connections */}
            {data.connections.length > 0 && (
              <div>
                <p className="text-[9px] font-mono text-nexus-text-secondary uppercase tracking-wider mb-1">
                  Connections ({data.connections.length})
                </p>
                <div className="space-y-0.5 max-h-28 overflow-y-auto">
                  {data.connections.map((conn, i) => (
                    <div key={i} className="flex items-center gap-1 text-[10px] font-mono">
                      <span className="text-nexus-text-secondary">{conn.direction === 'outgoing' ? '\u2192' : '\u2190'}</span>
                      <span className={REL_COLORS[conn.relType] || 'text-gray-400'}>{conn.relType}</span>
                      <span className="text-nexus-text truncate flex-1">{conn.name}</span>
                      <span className="text-nexus-text-secondary text-[8px]">{conn.type}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Position */}
            {data.position && (
              <div className="text-[10px] font-mono text-nexus-text-secondary">
                LAT: {data.position.latitude.toFixed(4)} LNG: {data.position.longitude.toFixed(4)}
                {data.lastSeen && <span className="ml-2">Last: {new Date(data.lastSeen).toLocaleTimeString()}</span>}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-1.5 pt-1 border-t border-nexus-border">
              <button
                onClick={() => {
                  if (!hasTrack && data.position) {
                    addTrackPoints(data.id, [{
                      position: data.position,
                      timestamp: new Date().toISOString(),
                    }]);
                  }
                  useMapStore.getState().setTrackingPanelOpen(true);
                }}
                className={`px-2 py-1 text-[9px] font-mono rounded border transition-colors ${
                  hasTrack
                    ? 'bg-nexus-cyan/20 text-nexus-cyan border-nexus-cyan/30'
                    : 'text-nexus-text-secondary border-nexus-border hover:text-nexus-text'
                }`}
              >
                {hasTrack ? 'Tracking' : 'Track'}
              </button>
              <button
                onClick={() => setActiveTab('graph')}
                className="px-2 py-1 text-[9px] font-mono text-nexus-text-secondary border border-nexus-border rounded hover:text-nexus-text transition-colors"
              >
                Graph
              </button>
              <button
                onClick={() => {
                  if (!detailPanelOpen) toggleDetailPanel();
                }}
                className="px-2 py-1 text-[9px] font-mono text-nexus-text-secondary border border-nexus-border rounded hover:text-nexus-text transition-colors"
              >
                Detail
              </button>
              <button
                onClick={async () => {
                  try {
                    const { investigations } = await import('@/services/api');
                    await investigations.create({
                      query: `Investigate ${data.name}`,
                      target_ints: [data.sourceInt],
                    });
                  } catch { /* ignore */ }
                }}
                className="px-2 py-1 text-[9px] font-mono text-amber-400 border border-amber-400/30 rounded hover:bg-amber-400/10 transition-colors"
              >
                Investigate
              </button>
            </div>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
