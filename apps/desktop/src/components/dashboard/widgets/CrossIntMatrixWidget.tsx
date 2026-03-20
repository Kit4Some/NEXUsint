import { useCallback, useEffect, useState } from 'react';
import { Card } from '@/components/common/Card';
import { fusion } from '@/services/api';

const INT_TYPES = ['CYBINT', 'SOCMINT', 'SIGINT', 'GEOINT'];
const INT_SHORT = { CYBINT: 'CYB', SOCMINT: 'SOC', SIGINT: 'SIG', GEOINT: 'GEO' };

export function CrossIntMatrixWidget() {
  const [matrix, setMatrix] = useState<Record<string, Record<string, number>> | null>(null);

  const fetchMatrix = useCallback(async () => {
    try {
      const data = (await fusion.getCorrelationMatrix()) as {
        matrix: Record<string, Record<string, number>>;
      };
      setMatrix(data.matrix);
    } catch {
      // API not ready
    }
  }, []);

  useEffect(() => {
    fetchMatrix();
  }, [fetchMatrix]);

  const getColor = (value: number) => {
    if (value === 0) return 'rgba(42,49,84,0.5)';
    const intensity = Math.min(value / 10, 1);
    return `rgba(0, 212, 255, ${0.1 + intensity * 0.5})`;
  };

  return (
    <Card className="p-4">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-3">
        Cross-INT Correlation Matrix
      </p>

      <div className="grid grid-cols-4 gap-1">
        {INT_TYPES.map((row) =>
          INT_TYPES.map((col) => {
            const value = matrix?.[row]?.[col] ?? 0;
            return (
              <div
                key={`${row}-${col}`}
                className="aspect-square rounded flex items-center justify-center text-[9px] font-mono text-nexus-text-primary cursor-default"
                style={{ backgroundColor: row === col ? 'rgba(0,212,255,0.2)' : getColor(value) }}
                title={`${row} x ${col}: ${value}`}
              >
                {row === col ? '-' : value}
              </div>
            );
          }),
        )}
      </div>

      <div className="flex justify-between mt-2 text-[9px] font-mono text-nexus-text-secondary">
        {INT_TYPES.map((int) => (
          <span key={int}>{INT_SHORT[int as keyof typeof INT_SHORT]}</span>
        ))}
      </div>
    </Card>
  );
}
