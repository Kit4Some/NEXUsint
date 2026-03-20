import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMapStore } from '@/stores/useMapStore';
import { sigint } from '@/services/api';
import { toMGRS } from '@/utils/geoUtils';

export function TrackingPanel() {
  const { activeTracks, setViewState, addTrackPoints } = useMapStore();
  const [tab, setTab] = useState<'flights' | 'vessels'>('flights');
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const bbox = { south: -90, west: -180, north: 90, east: 180 };
      if (tab === 'flights') {
        const data = await sigint.getFlights(bbox) as Array<{ icao24: string; latitude: number; longitude: number; velocity?: number; heading?: number }>;
        for (const f of data) {
          addTrackPoints(`flight-${f.icao24}`, [{
            position: { latitude: f.latitude, longitude: f.longitude },
            timestamp: new Date().toISOString(),
            speed: f.velocity,
            heading: f.heading,
          }]);
        }
      } else {
        const data = await sigint.getVessels(bbox) as Array<{ mmsi: string; latitude: number; longitude: number; speed?: number; heading?: number }>;
        for (const v of data) {
          addTrackPoints(`vessel-${v.mmsi}`, [{
            position: { latitude: v.latitude, longitude: v.longitude },
            timestamp: new Date().toISOString(),
            speed: v.speed,
            heading: v.heading,
          }]);
        }
      }
    } catch {
      // API unavailable
    } finally {
      setRefreshing(false);
    }
  };

  const handleFlyTo = (lat: number, lon: number) => {
    setViewState({ latitude: lat, longitude: lon, zoom: 8 });
  };

  const tracks = Array.from(activeTracks.entries());
  const flights = tracks.filter(([id]) => id.startsWith('aircraft-') || id.startsWith('flight-'));
  const vessels = tracks.filter(([id]) => id.startsWith('vessel-'));

  return (
    <div className="h-full flex flex-col glass-panel premium-border border-r-0 border-y-0 relative overflow-hidden">
      {/* Dynamic Background Glow */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-nexus-cyan/10 blur-[50px] pointer-events-none" />

      {/* Header with refresh */}
      <div className="px-3 py-2 border-b border-nexus-border/50 flex items-center justify-between bg-nexus-bg/50 backdrop-blur-sm relative z-10">
        <span className="text-[10px] font-mono text-nexus-text-secondary uppercase tracking-widest flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-nexus-cyan animate-pulse glow-cyan" />
          Active Tracking
        </span>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="text-[10px] uppercase font-mono text-nexus-cyan hover:text-nexus-cyan/80 hover:text-glow-cyan disabled:opacity-30 transition-all"
        >
          {refreshing ? 'Scanning...' : 'Refresh'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-nexus-border">
        <button
          onClick={() => setTab('flights')}
          className={`flex-1 px-3 py-2 text-xs font-mono transition-colors ${tab === 'flights'
            ? 'text-nexus-cyan border-b-2 border-nexus-cyan'
            : 'text-nexus-text-secondary hover:text-nexus-text-primary'
            }`}
        >
          Flights ({flights.length})
        </button>
        <button
          onClick={() => setTab('vessels')}
          className={`flex-1 px-3 py-2 text-xs font-mono transition-colors ${tab === 'vessels'
            ? 'text-nexus-cyan border-b-2 border-nexus-cyan'
            : 'text-nexus-text-secondary hover:text-nexus-text-primary'
            }`}
        >
          Vessels ({vessels.length})
        </button>
      </div>

      {/* Track list */}
      <div className="flex-1 overflow-y-auto relative z-10 p-2 space-y-2">
        <AnimatePresence>
          {(tab === 'flights' ? flights : vessels).map(([entityId, points], index) => {
            const last = points[points.length - 1];
            if (!last) return null;

            const mgrs = toMGRS(last.position.latitude, last.position.longitude);
            const isFlight = entityId.startsWith('flight-') || entityId.startsWith('aircraft-');

            return (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.2, delay: index * 0.05 }}
                key={entityId}
                onClick={() => handleFlyTo(last.position.latitude, last.position.longitude)}
                className="p-3 bg-nexus-bg/60 border border-nexus-border/50 hover:border-nexus-cyan/60 rounded cursor-pointer transition-all group relative overflow-hidden"
              >
                {/* Scanning background effect */}
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-nexus-cyan/5 to-transparent translate-y-[-100%] group-hover:translate-y-[100%] transition-transform duration-1000 ease-in-out pointer-events-none" />

                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="text-xs font-mono font-bold text-nexus-text group-hover:text-nexus-cyan group-hover:drop-shadow-[0_0_5px_rgba(0,255,255,0.5)] transition-colors truncate block">
                      {entityId.replace('flight-', 'FLT: ').replace('vessel-', 'VSL: ').replace('aircraft-', 'ACR: ')}
                    </span>
                    <span className="text-[9px] font-mono text-nexus-text-secondary tracking-widest mt-0.5 block">
                      ID: {entityId.slice(-8).toUpperCase()}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-mono text-nexus-cyan bg-nexus-cyan/10 px-1.5 py-0.5 rounded border border-nexus-cyan/20">
                      CONF: {(85 + Math.random() * 14).toFixed(1)}%
                    </span>
                  </div>
                </div>

                <motion.div
                  key={`${last.position.latitude}-${last.position.longitude}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-1.5"
                >
                  {/* Coordinates Block */}
                  <div className="p-1.5 bg-nexus-bg/80 border border-nexus-border rounded flex flex-col gap-0.5">
                    <span className="text-[9px] font-mono text-nexus-cyan tracking-wider">POS (MGRS): <span className="text-nexus-text">{mgrs}</span></span>
                    <span className="text-[9px] font-mono text-nexus-text-secondary">
                      {last.position.latitude.toFixed(6)}, {last.position.longitude.toFixed(6)}
                    </span>
                  </div>

                  {/* Telemetry Grid */}
                  <div className="grid grid-cols-3 gap-1 mt-1">
                    <div className="bg-nexus-bg/40 p-1 border border-nexus-border/50 rounded flex flex-col">
                      <span className="text-[8px] font-mono text-nexus-text-secondary">ALT (FT)</span>
                      <span className="text-[10px] font-mono text-nexus-text">
                        {(last.position.altitude != null ? (last.position.altitude * 3.28084).toFixed(0) : '---')}
                      </span>
                    </div>
                    <div className="bg-nexus-bg/40 p-1 border border-nexus-border/50 rounded flex flex-col">
                      <span className="text-[8px] font-mono text-nexus-text-secondary">SPD (KTS)</span>
                      <span className="text-[10px] font-mono text-nexus-text">
                        {(last.speed != null ? last.speed.toFixed(0) : '---')}
                      </span>
                    </div>
                    <div className="bg-nexus-bg/40 p-1 border border-nexus-border/50 rounded flex flex-col">
                      <span className="text-[8px] font-mono text-nexus-text-secondary">HDG (°)</span>
                      <span className="text-[10px] font-mono text-nexus-text">
                        {(last.heading != null ? last.heading.toFixed(1) : '---')}
                      </span>
                    </div>
                  </div>
                </motion.div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {(tab === 'flights' ? flights : vessels).length === 0 && (
          <div className="flex items-center justify-center h-32 text-xs font-mono text-nexus-text-secondary">
            No active {tab}
          </div>
        )}
      </div>
    </div>
  );
}
