import { clsx } from 'clsx';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'cyan' | 'green' | 'red' | 'amber';
  className?: string;
}

const variants = {
  default: 'bg-nexus-card text-nexus-text-secondary border-nexus-border',
  cyan: 'bg-nexus-cyan/10 text-nexus-cyan border-nexus-cyan/30',
  green: 'bg-nexus-green/10 text-nexus-green border-nexus-green/30',
  red: 'bg-nexus-red/10 text-nexus-red border-nexus-red/30',
  amber: 'bg-nexus-amber/10 text-nexus-amber border-nexus-amber/30',
};

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono rounded border',
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
