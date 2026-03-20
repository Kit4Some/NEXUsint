import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { clsx } from 'clsx';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';
import type { NewsArticle } from '@/types/livefeed';

// ---------------------------------------------------------------------------
// Types & constants
// ---------------------------------------------------------------------------

type RiskFilter = 'all' | 'critical' | 'high' | 'medium' | 'low';
type SortMode = 'risk' | 'time';

interface RiskConfig {
  label: string;
  short: string;
  bg: string;
  border: string;
  text: string;
  badge: string;
  dot: string;
}

const RISK_CONFIGS: Record<string, RiskConfig> = {
  critical: {
    label: 'Critical',
    short: 'CRIT',
    bg: 'bg-red-500/8',
    border: 'border-red-500/30',
    text: 'text-red-400',
    badge: 'bg-red-500/15 text-red-400 border-red-500/30',
    dot: 'bg-red-500',
  },
  high: {
    label: 'High',
    short: 'HIGH',
    bg: 'bg-orange-500/8',
    border: 'border-orange-500/30',
    text: 'text-orange-400',
    badge: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    dot: 'bg-orange-500',
  },
  medium: {
    label: 'Medium',
    short: 'MED',
    bg: 'bg-amber-500/8',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    dot: 'bg-amber-500',
  },
  low: {
    label: 'Low',
    short: 'LOW',
    bg: 'bg-emerald-500/8',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    dot: 'bg-emerald-500',
  },
};

function getRiskLevel(score: number): string {
  if (score >= 8) return 'critical';
  if (score >= 6) return 'high';
  if (score >= 4) return 'medium';
  return 'low';
}

function getRiskConfig(score: number): RiskConfig {
  return RISK_CONFIGS[getRiskLevel(score)];
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function RiskBadge({ score }: { score: number }) {
  const cfg = getRiskConfig(score);
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono font-bold rounded border shrink-0',
        cfg.badge,
      )}
    >
      LVL: {score}/10
    </span>
  );
}

function ClusterArticle({ article }: { article: NewsArticle }) {
  const cfg = getRiskConfig(article.risk_score);
  return (
    <div
      className={clsx(
        'p-2 rounded border transition-colors',
        cfg.bg,
        cfg.border,
      )}
    >
      <div className="flex items-center justify-between gap-2 mb-0.5">
        <span className="text-[9px] font-mono text-nexus-text-secondary truncate">
          {article.source}
        </span>
        <RiskBadge score={article.risk_score} />
      </div>
      <a
        href={article.link}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[11px] font-mono text-nexus-text hover:text-nexus-cyan transition-colors line-clamp-2"
      >
        {article.title}
      </a>
    </div>
  );
}

function ArticleCard({ article }: { article: NewsArticle }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = getRiskConfig(article.risk_score);
  const hasCluster = article.cluster_count > 1 && article.articles?.length > 0;

  return (
    <div
      className={clsx(
        'rounded-lg border transition-all duration-200',
        cfg.bg,
        cfg.border,
      )}
    >
      {/* Main card content */}
      <div className="p-2.5">
        {/* Top row: source + time + risk badge */}
        <div className="flex items-center justify-between gap-2 mb-1">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', cfg.dot)} />
            <span className="text-[10px] font-mono text-nexus-text-secondary truncate">
              {article.source}
            </span>
            <span className="text-[9px] font-mono text-nexus-text-secondary/60">
              {timeAgo(article.published)}
            </span>
          </div>
          <RiskBadge score={article.risk_score} />
        </div>

        {/* Title */}
        <a
          href={article.link}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-[12px] font-mono leading-snug text-nexus-text hover:text-nexus-cyan transition-colors mb-1"
        >
          {article.title}
        </a>

        {/* Machine assessment */}
        {article.machine_assessment && (
          <p className="text-[10px] font-mono text-nexus-text-secondary/80 leading-relaxed mt-1 border-l-2 border-nexus-border pl-2">
            {article.machine_assessment}
          </p>
        )}

        {/* Bottom row: cluster toggle */}
        {hasCluster && (
          <button
            onClick={() => setExpanded(!expanded)}
            className={clsx(
              'mt-1.5 flex items-center gap-1 px-1.5 py-0.5 text-[9px] font-mono rounded border transition-colors',
              expanded
                ? 'bg-nexus-cyan/15 text-nexus-cyan border-nexus-cyan/30'
                : 'bg-nexus-bg/50 text-nexus-text-secondary border-nexus-border hover:text-nexus-text hover:border-nexus-text-secondary',
            )}
          >
            <span
              className={clsx(
                'inline-block transition-transform duration-200',
                expanded && 'rotate-90',
              )}
            >
              {'\u25B6'}
            </span>
            {article.cluster_count - 1} related article
            {article.cluster_count - 1 !== 1 ? 's' : ''}
          </button>
        )}
      </div>

      {/* Expanded cluster articles */}
      <div
        className={clsx(
          'overflow-hidden transition-all duration-200',
          expanded ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0',
        )}
      >
        <div className="px-2.5 pb-2.5 space-y-1 border-t border-nexus-border/50 pt-2">
          <p className="text-[9px] font-mono uppercase tracking-wider text-nexus-text-secondary/60 mb-1">
            Cluster articles
          </p>
          {article.articles.map((sub, idx) => (
            <ClusterArticle key={`${sub.link}-${idx}`} article={sub} />
          ))}
        </div>
      </div>
    </div>
  );
}

function FilterBar({
  riskFilter,
  setRiskFilter,
  sortMode,
  setSortMode,
  searchText,
  setSearchText,
}: {
  riskFilter: RiskFilter;
  setRiskFilter: (f: RiskFilter) => void;
  sortMode: SortMode;
  setSortMode: (s: SortMode) => void;
  searchText: string;
  setSearchText: (t: string) => void;
}) {
  const filterOptions: { id: RiskFilter; label: string; color: string }[] = [
    { id: 'all', label: 'ALL', color: 'text-nexus-text-secondary' },
    { id: 'critical', label: 'CRIT', color: 'text-red-400' },
    { id: 'high', label: 'HIGH', color: 'text-orange-400' },
    { id: 'medium', label: 'MED', color: 'text-amber-400' },
    { id: 'low', label: 'LOW', color: 'text-emerald-400' },
  ];

  return (
    <div className="px-3 py-2 space-y-2 border-b border-nexus-border">
      {/* Risk filter buttons */}
      <div className="flex items-center gap-1">
        {filterOptions.map((opt) => (
          <button
            key={opt.id}
            onClick={() => setRiskFilter(opt.id)}
            className={clsx(
              'px-2 py-0.5 text-[10px] font-mono rounded border transition-colors',
              riskFilter === opt.id
                ? clsx(opt.color, 'border-current bg-current/10')
                : 'text-nexus-text-secondary/60 border-transparent hover:text-nexus-text-secondary hover:border-nexus-border',
            )}
          >
            {opt.label}
          </button>
        ))}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Sort toggle */}
        <button
          onClick={() => setSortMode(sortMode === 'risk' ? 'time' : 'risk')}
          className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono text-nexus-text-secondary border border-nexus-border rounded hover:text-nexus-text hover:border-nexus-text-secondary transition-colors"
          title={`Sort by ${sortMode === 'risk' ? 'time' : 'risk score'}`}
        >
          {sortMode === 'risk' ? '\u2193 RISK' : '\u2193 TIME'}
        </button>
      </div>

      {/* Search input */}
      <div className="relative">
        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-nexus-text-secondary/50 text-[10px] font-mono">
          {'\u2315'}
        </span>
        <input
          type="text"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Filter by title..."
          className="w-full pl-6 pr-2 py-1 text-[11px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text placeholder:text-nexus-text-secondary/40 focus:border-nexus-cyan/50 focus:outline-none transition-colors"
        />
        {searchText && (
          <button
            onClick={() => setSearchText('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-nexus-text-secondary/50 hover:text-nexus-text text-[10px] transition-colors"
          >
            {'\u2715'}
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function NewsFeedPanel() {
  const news = useLiveFeedStore((s) => s.news);

  const [riskFilter, setRiskFilter] = useState<RiskFilter>('all');
  const [sortMode, setSortMode] = useState<SortMode>('risk');
  const [searchText, setSearchText] = useState('');

  const scrollRef = useRef<HTMLDivElement>(null);
  const prevHighRiskCount = useRef(0);

  // Filtered + sorted articles
  const filteredArticles = useMemo(() => {
    let items = [...news];

    // Apply risk filter
    if (riskFilter !== 'all') {
      items = items.filter((a) => getRiskLevel(a.risk_score) === riskFilter);
    }

    // Apply search filter
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      items = items.filter((a) => a.title.toLowerCase().includes(q));
    }

    // Sort
    if (sortMode === 'risk') {
      items.sort((a, b) => b.risk_score - a.risk_score);
    } else {
      items.sort(
        (a, b) =>
          new Date(b.published).getTime() - new Date(a.published).getTime(),
      );
    }

    return items;
  }, [news, riskFilter, sortMode, searchText]);

  // Count by risk level
  const riskCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const a of news) {
      const level = getRiskLevel(a.risk_score) as keyof typeof counts;
      counts[level]++;
    }
    return counts;
  }, [news]);

  // Auto-scroll to top when new high-risk items appear
  const autoScroll = useCallback(() => {
    const highRiskCount = news.filter((a) => a.risk_score > 7).length;
    if (highRiskCount > prevHighRiskCount.current && scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
    prevHighRiskCount.current = highRiskCount;
  }, [news]);

  useEffect(() => {
    autoScroll();
  }, [autoScroll]);

  return (
    <div className="h-full flex flex-col bg-nexus-bg-secondary overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2.5 border-b border-nexus-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <h2 className="text-xs font-mono uppercase tracking-wider text-nexus-cyan font-bold">
              Global Threat Intercept
            </h2>
          </div>
          <span className="text-[10px] font-mono text-nexus-text-secondary">
            {news.length} article{news.length !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Risk summary bar */}
        <div className="flex items-center gap-3 mt-1.5">
          {(
            [
              ['critical', riskCounts.critical],
              ['high', riskCounts.high],
              ['medium', riskCounts.medium],
              ['low', riskCounts.low],
            ] as const
          ).map(([level, count]) => {
            const cfg = RISK_CONFIGS[level];
            return (
              <div key={level} className="flex items-center gap-1">
                <span className={clsx('w-1.5 h-1.5 rounded-full', cfg.dot)} />
                <span className={clsx('text-[9px] font-mono', cfg.text)}>
                  {count}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Filter controls */}
      <FilterBar
        riskFilter={riskFilter}
        setRiskFilter={setRiskFilter}
        sortMode={sortMode}
        setSortMode={setSortMode}
        searchText={searchText}
        setSearchText={setSearchText}
      />

      {/* Article list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-1.5">
          {filteredArticles.length === 0 && news.length > 0 && (
            <div className="text-center py-8">
              <p className="text-[10px] font-mono text-nexus-text-secondary/50">
                No articles match current filters
              </p>
              <button
                onClick={() => {
                  setRiskFilter('all');
                  setSearchText('');
                }}
                className="mt-1 text-[10px] font-mono text-nexus-cyan/70 hover:text-nexus-cyan transition-colors"
              >
                Clear filters
              </button>
            </div>
          )}

          {filteredArticles.length === 0 && news.length === 0 && (
            <div className="text-center py-12">
              <p className="text-[10px] font-mono text-nexus-text-secondary/50">
                No threat intelligence received
              </p>
              <p className="text-[9px] font-mono text-nexus-text-secondary/30 mt-1">
                Start the live feed to begin monitoring global threats
              </p>
            </div>
          )}

          {filteredArticles.map((article, idx) => (
            <ArticleCard key={`${article.link}-${idx}`} article={article} />
          ))}
        </div>

        {/* Bottom padding for comfortable scrolling */}
        {filteredArticles.length > 0 && <div className="h-4" />}
      </div>

      {/* Footer status */}
      <div className="px-3 py-1.5 border-t border-nexus-border flex items-center justify-between">
        <span className="text-[9px] font-mono text-nexus-text-secondary/50">
          {filteredArticles.length !== news.length
            ? `${filteredArticles.length} / ${news.length} shown`
            : `${news.length} total`}
        </span>
        <span className="text-[9px] font-mono text-nexus-text-secondary/50">
          {sortMode === 'risk' ? 'Sorted by risk' : 'Sorted by time'}
        </span>
      </div>
    </div>
  );
}
