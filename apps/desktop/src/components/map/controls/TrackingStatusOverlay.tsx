import { useMapStore } from '@/stores/useMapStore';
import { useAppStore } from '@/stores/useAppStore';

export function TrackingStatusOverlay() {
  const { activeTracks, geofences, playbackState } = useMapStore();
  const { connectionStatus, entityCount } = useAppStore();

  const trackEntries = Array.from(activeTracks.entries());
  const flightCount = trackEntries.filter(([id]) => id.startsWith('aircraft-') || id.startsWith('flight-')).length;
  const vesselCount = trackEntries.filter(([id]) => id.startsWith('vessel-')).length;
  const entityTracks = trackEntries.length - flightCount - vesselCount;

  const wsColor = connectionStatus === 'connected'
    ? 'text-green-400'
    : connectionStatus === 'connecting'
    ? 'text-amber-400 animate-pulse'
    : 'text-red-400';

  const wsLabel = connectionStatus === 'connected' ? 'CONNECTED' : connectionStatus === 'connecting' ? 'CONNECTING' : 'OFFLINE';

  return (
    <div className="absolute top-16 left-3 z-20 bg-nexus-card/90 backdrop-blur-sm border border-nexus-border rounded-lg px-2.5 py-2 min-w-[140px] shadow-lg">
      <p className="text-[8px] font-mono text-nexus-cyan uppercase tracking-[0.15em] mb-1.5">Tracking Status</p>

      <div className="space-y-1 text-[10px] font-mono">
        {flightCount > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-nexus-text-secondary">Flights</span>
            <span className="text-cyan-400">{flightCount} active</span>
          </div>
        )}
        {vesselCount > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-nexus-text-secondary">Vessels</span>
            <span className="text-teal-400">{vesselCount} active</span>
          </div>
        )}
        {entityTracks > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-nexus-text-secondary">Entities</span>
            <span className="text-blue-400">{entityTracks} tracked</span>
          </div>
        )}
        <div className="flex items-center justify-between">
          <span className="text-nexus-text-secondary">In View</span>
          <span className="text-nexus-text">{entityCount}</span>
        </div>
        {geofences.length > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-nexus-text-secondary">Geofences</span>
            <span className="text-amber-400">{geofences.length}</span>
          </div>
        )}
        {playbackState !== 'stopped' && (
          <div className="flex items-center justify-between">
            <span className="text-nexus-text-secondary">Playback</span>
            <span className={playbackState === 'playing' ? 'text-green-400' : 'text-amber-400'}>
              {playbackState.toUpperCase()}
            </span>
          </div>
        )}
      </div>

      <div className="mt-1.5 pt-1 border-t border-nexus-border/50 flex items-center gap-1">
        <div className={`w-1.5 h-1.5 rounded-full ${connectionStatus === 'connected' ? 'bg-green-400' : connectionStatus === 'connecting' ? 'bg-amber-400 animate-pulse' : 'bg-red-400'}`} />
        <span className={`text-[8px] font-mono uppercase tracking-wider ${wsColor}`}>WS: {wsLabel}</span>
      </div>
    </div>
  );
}
