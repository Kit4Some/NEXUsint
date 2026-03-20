import { type ButtonHTMLAttributes } from 'react';
import { clsx } from 'clsx';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: 'sm' | 'md';
}

const variants: Record<Variant, string> = {
  primary:
    'bg-nexus-cyan/10 text-nexus-cyan border-nexus-cyan/30 hover:bg-nexus-cyan/20 hover:border-nexus-cyan/50 glow-cyan',
  secondary:
    'bg-nexus-card text-nexus-text border-nexus-border hover:bg-nexus-border/50',
  danger:
    'bg-nexus-red/10 text-nexus-red border-nexus-red/30 hover:bg-nexus-red/20',
  ghost:
    'bg-transparent text-nexus-text-secondary border-transparent hover:bg-nexus-card hover:text-nexus-text',
};

export function Button({ variant = 'secondary', size = 'md', className, children, ...props }: ButtonProps) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-1.5 rounded border font-medium transition-all',
        size === 'sm' ? 'px-2 py-1 text-xs' : 'px-3 py-1.5 text-sm',
        variants[variant],
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
