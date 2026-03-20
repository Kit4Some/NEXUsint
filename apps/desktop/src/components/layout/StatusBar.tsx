import { clsx } from 'clsx';
import { useAppStore } from '@/stores/useAppStore';

export function StatusBar() {
  const { connectionStatus, entityCount, relationshipCount, activeCollections, lastUpdate } =
    useAppStore();

  return (
    <div className="flex items-center h-6 bg-nexus-bg border-t border-nexus-border px-3 gap-4 text-[10px] font-mono text-nexus-text-secondary">
      {/* Connection Status */}
      <div className="flex items-center gap-1.5">
        <div
          className={clsx(
            'status-dot',
            connectionStatus === 'connected' ? 'connected' : 'disconnected',
          )}
        />
        <span className={connectionStatus === 'connected' ? 'text-nexus-green' : 'text-nexus-red'}>
          {connectionStatus === 'connected' ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      {/* Divider */}
      <div className="w-px h-3 bg-nexus-border" />

      {/* Entity count */}
      <span>
        Entities: <span className="text-nexus-text">{entityCount.toLocaleString()}</span>
      </span>

      {/* Relationship count */}
      <span>
        Relations: <span className="text-nexus-text">{relationshipCount.toLocaleString()}</span>
      </span>

      {/* Divider */}
      <div className="w-px h-3 bg-nexus-border" />

      {/* Active collections */}
      {activeCollections > 0 && (
        <span className="text-nexus-amber">
          Active Collections: {activeCollections}
        </span>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Last update */}
      {lastUpdate && <span>Last Update: {lastUpdate}</span>}

      {/* Version */}
      <span>v0.1.0</span>
    </div>
  );
}
