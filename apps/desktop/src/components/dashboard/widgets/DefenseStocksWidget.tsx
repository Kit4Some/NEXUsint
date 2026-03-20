import { Card } from '@/components/common/Card';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';
import type { StockData } from '@/types/livefeed';

const DEFENSE_SYMBOLS = ['RTX', 'LMT', 'NOC', 'GD', 'BA', 'PLTR'] as const;

const SYMBOL_NAMES: Record<string, string> = {
  RTX: 'Raytheon',
  LMT: 'Lockheed Martin',
  NOC: 'Northrop Grumman',
  GD: 'General Dynamics',
  BA: 'Boeing',
  PLTR: 'Palantir',
};

function StockRow({ stock }: { stock: StockData }) {
  const changeColor = stock.up ? 'text-emerald-400' : 'text-red-400';
  const arrow = stock.up ? '▲' : '▼';
  const sign = stock.up ? '+' : '';

  return (
    <div className="flex items-center justify-between py-1.5 border-b border-nexus-border/30 last:border-b-0">
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono font-bold text-nexus-cyan w-10">
          {stock.symbol}
        </span>
        <span className="text-[10px] font-mono text-nexus-text-secondary">
          {SYMBOL_NAMES[stock.symbol] || stock.symbol}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono text-nexus-text-primary tabular-nums">
          ${stock.price.toFixed(2)}
        </span>
        <span className={`text-[11px] font-mono tabular-nums ${changeColor} flex items-center gap-0.5 min-w-[70px] justify-end`}>
          <span className="text-[9px]">{arrow}</span>
          {sign}{stock.change_percent.toFixed(2)}%
        </span>
      </div>
    </div>
  );
}

function EmptyRow({ symbol }: { symbol: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-nexus-border/30 last:border-b-0">
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono font-bold text-nexus-text-secondary/50 w-10">
          {symbol}
        </span>
        <span className="text-[10px] font-mono text-nexus-text-secondary/40">
          {SYMBOL_NAMES[symbol] || symbol}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono text-nexus-text-secondary/40 tabular-nums">
          ---.--
        </span>
        <span className="text-[11px] font-mono text-nexus-text-secondary/40 tabular-nums min-w-[70px] text-right">
          --.---%
        </span>
      </div>
    </div>
  );
}

export function DefenseStocksWidget() {
  const stocks = useLiveFeedStore((s) => s.stocks);
  const hasData = Object.keys(stocks).length > 0;

  const avgChange = hasData
    ? DEFENSE_SYMBOLS.reduce((sum, sym) => {
        const s = stocks[sym];
        return s ? sum + s.change_percent : sum;
      }, 0) / DEFENSE_SYMBOLS.filter((sym) => stocks[sym]).length
    : 0;

  const avgColor = avgChange >= 0 ? 'text-emerald-400' : 'text-red-400';
  const avgArrow = avgChange >= 0 ? '▲' : '▼';
  const avgSign = avgChange >= 0 ? '+' : '';

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary">
          Defense Sector
        </p>
        {hasData && (
          <span className={`text-[10px] font-mono ${avgColor}`}>
            {avgArrow} Avg {avgSign}{avgChange.toFixed(2)}%
          </span>
        )}
      </div>

      <div className="space-y-0">
        {DEFENSE_SYMBOLS.map((symbol) => {
          const stock = stocks[symbol];
          return stock ? (
            <StockRow key={symbol} stock={stock} />
          ) : (
            <EmptyRow key={symbol} symbol={symbol} />
          );
        })}
      </div>

      {!hasData && (
        <p className="text-[10px] font-mono text-nexus-text-secondary/50 mt-2 text-center italic">
          Awaiting market data feed
        </p>
      )}
    </Card>
  );
}
