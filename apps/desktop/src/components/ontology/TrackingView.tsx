import { motion } from 'framer-motion';
import { clsx } from 'clsx';

interface TrackingData {
  entity: {
    id: string;
    name: string;
    type: string;
    sourceInt: string;
    confidence: number;
    riskScore: number;
    firstSeen: string;
    lastSeen: string;
  };
  relationships: Array<{
    neighborId: string;
    neighborName: string;
    neighborType: string;
    neighborSourceInt: string;
    relType: string;
    relConfidence: number | null;
    relFirstSeen: string | null;
    relLastSeen: string | null;
    direction: 'outgoing' | 'incoming';
  }>;
  locationTrail: Array<{
    locationId: string;
    locationName: string;
    latitude: number | null;
    longitude: number | null;
    firstSeen: string | null;
    lastSeen: string | null;
  }>;
  extendedNetwork: Array<{
    via: { id: string; name: string; type: string; rel: string };
    target: { id: string; name: string; type: string; rel: string };
    targetSourceInt: string;
  }>;
  intSourceBreakdown: Record<string, number>;
  totalConnections: number;
  totalLocations: number;
}

interface InferenceData {
  entityId: string;
  inferences: Array<{
    rule: string;
    chain: string;
    via: { id: string; name: string; type: string };
    inferred: { id: string; name: string; type: string };
    confidence: number;
  }>;
  totalInferred: number;
}

const INT_COLORS: Record<string, string> = {
  CYBINT: 'text-red-400 bg-red-500/10 border-red-500/20',
  SOCMINT: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  SIGINT: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  GEOINT: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  UNKNOWN: 'text-gray-400 bg-gray-500/10 border-gray-500/20',
};

function IntSourceBadge({ source }: { source: string }) {
  const style = INT_COLORS[source] || INT_COLORS.UNKNOWN;
  return (
    <span className={clsx('px-1.5 py-0.5 rounded text-[9px] font-mono border', style)}>
      {source}
    </span>
  );
}

export function TrackingPanel({ data, onClose }: { data: TrackingData; onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-3 space-y-3 overflow-y-auto h-full"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-xs font-mono uppercase tracking-wider text-nexus-cyan">
            Entity Tracking
          </h4>
          <p className="text-[10px] text-nexus-text-secondary mt-0.5">
            {data.entity.name} — {data.totalConnections} connections, {data.totalLocations} locations
          </p>
        </div>
        <button onClick={onClose} className="text-nexus-text-secondary hover:text-nexus-text text-xs">
          Back
        </button>
      </div>

      {/* INT Source Breakdown */}
      <div className="glass-panel rounded p-2">
        <p className="text-[10px] font-mono text-nexus-text-secondary mb-1.5">INT Sources</p>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(data.intSourceBreakdown).map(([src, count]) => (
            <div key={src} className="flex items-center gap-1">
              <IntSourceBadge source={src} />
              <span className="text-[10px] font-mono text-nexus-text">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Location Trail */}
      {data.locationTrail.length > 0 && (
        <div className="glass-panel rounded p-2">
          <p className="text-[10px] font-mono text-nexus-text-secondary mb-1.5">
            Location Trail ({data.locationTrail.length})
          </p>
          <div className="space-y-1.5">
            {data.locationTrail.map((loc, i) => (
              <motion.div
                key={loc.locationId}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center gap-2 text-[10px]"
              >
                <div className="w-4 h-4 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
                  <span className="text-[8px] text-emerald-400">{i + 1}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <span className="font-mono text-nexus-text truncate block">{loc.locationName}</span>
                  {loc.latitude && loc.longitude && (
                    <span className="text-nexus-text-secondary">
                      {loc.latitude.toFixed(2)}, {loc.longitude.toFixed(2)}
                    </span>
                  )}
                </div>
                {loc.firstSeen && (
                  <span className="text-nexus-text-secondary text-[9px] flex-shrink-0">
                    {new Date(loc.firstSeen).toLocaleDateString()}
                  </span>
                )}
                {i < data.locationTrail.length - 1 && (
                  <div className="absolute left-[7px] top-[20px] w-px h-3 bg-emerald-500/30" />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Direct Relationships */}
      <div className="glass-panel rounded p-2">
        <p className="text-[10px] font-mono text-nexus-text-secondary mb-1.5">
          Direct Relationships ({data.relationships.length})
        </p>
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {data.relationships.map((rel, i) => (
            <div key={`${rel.neighborId}-${i}`} className="flex items-center gap-1.5 text-[10px] py-0.5">
              <span className={clsx(
                'text-[9px] px-1 py-0.5 rounded font-mono',
                rel.direction === 'outgoing' ? 'bg-cyan-500/10 text-cyan-400' : 'bg-purple-500/10 text-purple-400'
              )}>
                {rel.direction === 'outgoing' ? '→' : '←'} {rel.relType}
              </span>
              <span className="font-mono text-nexus-text truncate flex-1">{rel.neighborName}</span>
              <IntSourceBadge source={rel.neighborSourceInt || 'UNKNOWN'} />
            </div>
          ))}
        </div>
      </div>

      {/* Extended Network (2-hop) */}
      {data.extendedNetwork.length > 0 && (
        <div className="glass-panel rounded p-2">
          <p className="text-[10px] font-mono text-nexus-text-secondary mb-1.5">
            Extended Network — 2-hop ({data.extendedNetwork.length})
          </p>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {data.extendedNetwork.map((item, i) => (
              <div key={i} className="text-[10px] py-0.5 flex items-center gap-1">
                <span className="text-nexus-text-secondary font-mono">via</span>
                <span className="text-nexus-text font-mono truncate">{item.via.name}</span>
                <span className="text-[9px] px-1 rounded bg-nexus-card text-nexus-text-secondary">
                  {item.via.rel} → {item.target.rel}
                </span>
                <span className="text-nexus-cyan font-mono truncate">{item.target.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export function InferencePanel({ data, onClose }: { data: InferenceData; onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-3 space-y-3 overflow-y-auto h-full"
    >
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-xs font-mono uppercase tracking-wider text-amber-400">
            Ontology Reasoning
          </h4>
          <p className="text-[10px] text-nexus-text-secondary mt-0.5">
            {data.totalInferred} inferred relationships
          </p>
        </div>
        <button onClick={onClose} className="text-nexus-text-secondary hover:text-nexus-text text-xs">
          Back
        </button>
      </div>

      {data.inferences.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-xs text-nexus-text-secondary">No implicit relationships found.</p>
          <p className="text-[10px] text-nexus-text-secondary mt-1">
            Add more entities and relationships to enable ontology reasoning.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.inferences.map((inf, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass-panel rounded p-2"
            >
              <div className="flex items-center justify-between mb-1">
                <span className={clsx(
                  'text-[9px] px-1.5 py-0.5 rounded font-mono border',
                  inf.confidence >= 0.7 ? 'text-green-400 bg-green-500/10 border-green-500/20' :
                    inf.confidence >= 0.5 ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' :
                      'text-red-400 bg-red-500/10 border-red-500/20'
                )}>
                  {Math.round(inf.confidence * 100)}% confidence
                </span>
                <span className="text-[9px] font-mono text-nexus-text-secondary">{inf.rule}</span>
              </div>

              <div className="flex items-center gap-1.5 text-[10px]">
                <span className="text-nexus-text-secondary">via</span>
                <span className="font-mono text-nexus-text">{inf.via.name}</span>
                <span className="text-[9px] text-amber-400 font-mono">({inf.chain})</span>
              </div>

              <div className="flex items-center gap-1.5 text-[10px] mt-0.5">
                <span className="text-nexus-text-secondary">→</span>
                <span className="font-mono text-nexus-cyan">{inf.inferred.name}</span>
                <span className="text-[9px] text-nexus-text-secondary">({inf.inferred.type})</span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
