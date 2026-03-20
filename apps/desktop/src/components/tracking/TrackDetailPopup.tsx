import type { TrackPoint } from '@/types';

interface TrackDetailPopupProps {
  entityName: string;
  entityType: string;
  point: TrackPoint;
}

export function TrackDetailPopup({ entityName, entityType, point }: TrackDetailPopupProps) {
  return (
    <div className="bg-nexus-card border border-nexus-border rounded-lg shadow-xl px-3 py-2 min-w-[180px]">
      <div className="text-xs font-mono text-nexus-cyan font-bold truncate">{entityName}</div>
      <div className="text-[10px] font-mono text-nexus-text-secondary mt-0.5">{entityType}</div>

      <div className="border-t border-nexus-border/50 mt-1.5 pt-1.5 space-y-0.5">
        <InfoRow label="LAT" value={point.position.latitude.toFixed(5)} />
        <InfoRow label="LON" value={point.position.longitude.toFixed(5)} />
        {point.position.altitude != null && (
          <InfoRow label="ALT" value={`${point.position.altitude.toFixed(0)} m`} />
        )}
        {point.speed != null && <InfoRow label="SPD" value={`${point.speed.toFixed(1)} kts`} />}
        {point.heading != null && <InfoRow label="HDG" value={`${point.heading.toFixed(0)}°`} />}
        <InfoRow label="TIME" value={new Date(point.timestamp).toLocaleTimeString()} />
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-[10px] font-mono">
      <span className="text-nexus-text-secondary">{label}</span>
      <span className="text-nexus-text-primary">{value}</span>
    </div>
  );
}
