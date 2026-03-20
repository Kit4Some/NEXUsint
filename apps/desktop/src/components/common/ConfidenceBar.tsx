import { clsx } from 'clsx';

interface ConfidenceBarProps {
  value: number; // 0.0 - 1.0
  className?: string;
  showLabel?: boolean;
}

function getColor(value: number): string {
  if (value >= 0.8) return 'bg-nexus-green';
  if (value >= 0.5) return 'bg-nexus-cyan';
  if (value >= 0.3) return 'bg-nexus-amber';
  return 'bg-nexus-red';
}

export function ConfidenceBar({ value, className, showLabel = true }: ConfidenceBarProps) {
  const percent = Math.round(value * 100);

  return (
    <div className={clsx('flex items-center gap-2', className)}>
      <div className="flex-1 h-1.5 bg-nexus-bg rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all', getColor(value))}
          style={{ width: `${percent}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-[10px] font-mono text-nexus-text-secondary w-8 text-right">
          {percent}%
        </span>
      )}
    </div>
  );
}
