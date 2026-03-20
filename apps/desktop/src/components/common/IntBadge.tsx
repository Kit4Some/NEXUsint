import { Badge } from './Badge';

const INT_COLORS: Record<string, 'cyan' | 'green' | 'red' | 'amber'> = {
  SOCMINT: 'cyan',
  GEOINT: 'green',
  SIGINT: 'amber',
  CYBINT: 'red',
};

interface IntBadgeProps {
  intType: string;
}

export function IntBadge({ intType }: IntBadgeProps) {
  const variant = INT_COLORS[intType] ?? 'default';
  return <Badge variant={variant as 'cyan' | 'green' | 'red' | 'amber'}>{intType}</Badge>;
}
