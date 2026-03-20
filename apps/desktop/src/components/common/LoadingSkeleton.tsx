import { clsx } from 'clsx';

interface SkeletonProps {
  className?: string;
}

export function LoadingSkeleton({ className }: SkeletonProps) {
  return (
    <div
      className={clsx(
        'animate-pulse bg-nexus-border/30 rounded',
        className,
      )}
    />
  );
}

export function EntitySkeleton() {
  return (
    <div className="flex items-center gap-3 p-3">
      <LoadingSkeleton className="w-8 h-8 rounded-full" />
      <div className="flex-1 space-y-2">
        <LoadingSkeleton className="h-3 w-32" />
        <LoadingSkeleton className="h-2 w-20" />
      </div>
    </div>
  );
}
