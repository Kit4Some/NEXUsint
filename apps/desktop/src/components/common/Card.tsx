import { clsx } from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  glow?: 'cyan' | 'green' | 'red' | 'amber' | null;
}

export function Card({ children, className, glow = null }: CardProps) {
  return (
    <div
      className={clsx(
        'bg-nexus-card/80 border border-nexus-border rounded-lg',
        glow === 'cyan' && 'glow-cyan',
        glow === 'green' && 'glow-green',
        glow === 'red' && 'glow-red',
        glow === 'amber' && 'glow-amber',
        className,
      )}
    >
      {children}
    </div>
  );
}
