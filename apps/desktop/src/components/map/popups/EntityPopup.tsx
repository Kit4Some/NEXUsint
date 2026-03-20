import { Badge } from '@/components/common/Badge';
import { ConfidenceBar } from '@/components/common/ConfidenceBar';
import { IntBadge } from '@/components/common/IntBadge';
import { getEntityIconSvgUri, getEntityColor } from '../icons/entityIcons';

interface EntityPopupProps {
  entity: {
    id: string;
    type: string;
    name: string;
    confidence: number;
    sourceInt: string;
    riskScore: number;
    activity?: string;
    activityType?: string;
  };
}

const ACTIVITY_COLOR_MAP: Record<string, string> = {
  alert: 'bg-red-500',
  scanning: 'bg-amber-400',
  moving: 'bg-green-400',
  communicating: 'bg-cyan-400',
  idle: 'bg-gray-400',
};

export function EntityPopup({ entity }: EntityPopupProps) {
  const iconUri = getEntityIconSvgUri(entity.type, 18);
  const color = getEntityColor(entity.type);

  return (
    <div className="bg-nexus-card border border-nexus-border rounded-lg p-2.5 shadow-xl min-w-[180px]">
      <div className="flex items-center gap-2 mb-1.5">
        <img src={iconUri} alt={entity.type} className="w-[18px] h-[18px] flex-shrink-0" />
        <span className="text-sm font-medium text-nexus-text">{entity.name}</span>
      </div>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Badge variant="cyan">{entity.type}</Badge>
        <IntBadge intType={entity.sourceInt} />
      </div>
      {entity.activity && (
        <div className="flex items-center gap-1.5 mb-1.5">
          <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${ACTIVITY_COLOR_MAP[entity.activityType || 'idle'] || ACTIVITY_COLOR_MAP.idle}`} />
          <span className="text-[10px] font-mono italic text-nexus-text-secondary">{entity.activity}</span>
        </div>
      )}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-nexus-text-secondary">Confidence</span>
        </div>
        <ConfidenceBar value={entity.confidence} />
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-nexus-text-secondary">Risk</span>
          <span className="text-nexus-text font-mono">{entity.riskScore}/10</span>
        </div>
      </div>
    </div>
  );
}
