import { useState, useCallback, useEffect, useRef } from 'react';
import { useAppStore } from '@/stores/useAppStore';
import { useEntityStore } from '@/stores/useEntityStore';
import { useFulltextSearch, useSemanticSearch } from '@/hooks/useSearch';

type SearchMode = 'fulltext' | 'semantic' | 'all';

const ENTITY_ICONS: Record<string, string> = {
  Person: '\u25C9',
  Organization: '\u25A0',
  Location: '\u25B2',
  IP: '\u25C6',
  Domain: '\u25CE',
  Email: '\u2709',
  Hash: '#',
  URL: '\u29C9',
  Vulnerability: '\u26A0',
  Malware: '\u2623',
  default: '\u25CB',
};

function getEntityIcon(type: string) {
  return ENTITY_ICONS[type] || ENTITY_ICONS.default;
}

function ConfidenceBar({ score }: { score: number }) {
  const width = Math.min(Math.max(score * 100, 0), 100);
  const color = score >= 0.8 ? 'bg-nexus-green' : score >= 0.5 ? 'bg-nexus-amber' : 'bg-nexus-red';
  return (
    <div className="w-16 h-1.5 bg-nexus-bg rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${width}%` }} />
    </div>
  );
}

export function SearchOverlay() {
  const { searchOverlayOpen, setSearchOverlayOpen } = useAppStore();
  const { setSelectedEntityId, setDetailPanelOpen } = useEntityStore();
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<SearchMode>('fulltext');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // Debounce query
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const fulltext = useFulltextSearch(
    debouncedQuery,
    undefined,
  );
  const semantic = useSemanticSearch(debouncedQuery);

  const showFulltext = mode === 'fulltext' || mode === 'all';
  const showSemantic = mode === 'semantic' || mode === 'all';

  // Combine results
  const results: Array<{ id: string; name: string; type: string; score: number; source: 'fulltext' | 'semantic' }> = [];

  if (showFulltext && fulltext.data?.hits) {
    for (const hit of fulltext.data.hits) {
      results.push({ id: hit.id, name: hit.name, type: hit.type, score: hit.score, source: 'fulltext' });
    }
  }
  if (showSemantic && semantic.data) {
    for (const item of semantic.data) {
      if (!results.some((r) => r.id === item.entity_id)) {
        results.push({ id: item.entity_id, name: item.entity_name, type: item.entity_type, score: item.similarity, source: 'semantic' });
      }
    }
  }

  // Auto-focus input on open
  useEffect(() => {
    if (searchOverlayOpen) {
      setQuery('');
      setDebouncedQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [searchOverlayOpen]);

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [debouncedQuery, mode]);

  const handleSelect = useCallback(
    (id: string) => {
      setSelectedEntityId(id);
      setDetailPanelOpen(true);
      setSearchOverlayOpen(false);
    },
    [setSelectedEntityId, setDetailPanelOpen, setSearchOverlayOpen],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && results[selectedIndex]) {
        e.preventDefault();
        handleSelect(results[selectedIndex].id);
      } else if (e.key === 'Escape') {
        setSearchOverlayOpen(false);
      }
    },
    [results, selectedIndex, handleSelect, setSearchOverlayOpen],
  );

  if (!searchOverlayOpen) return null;

  const isLoading = fulltext.isLoading || semantic.isLoading;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={() => setSearchOverlayOpen(false)}
      />

      {/* Search Panel */}
      <div className="relative w-[640px] bg-nexus-card border border-nexus-border rounded-lg shadow-2xl overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center border-b border-nexus-border">
          <span className="pl-4 text-nexus-cyan text-lg">{'\u2315'}</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search entities..."
            className="flex-1 px-3 py-3 bg-transparent text-sm text-nexus-text outline-none placeholder:text-nexus-text-secondary font-mono"
            autoFocus
          />
          {isLoading && (
            <div className="pr-4">
              <div className="w-4 h-4 border-2 border-nexus-cyan/30 border-t-nexus-cyan rounded-full animate-spin" />
            </div>
          )}
          <kbd className="mr-4 text-[10px] px-1.5 py-0.5 rounded bg-nexus-bg border border-nexus-border font-mono text-nexus-text-secondary">
            Ctrl+/
          </kbd>
        </div>

        {/* Mode Tabs */}
        <div className="flex gap-1 px-3 py-2 border-b border-nexus-border">
          {(['fulltext', 'semantic', 'all'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
                mode === m
                  ? 'bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/30'
                  : 'text-nexus-text-secondary hover:text-nexus-text hover:bg-nexus-bg'
              }`}
            >
              {m === 'fulltext' ? 'Full Text' : m === 'semantic' ? 'Semantic' : 'All'}
            </button>
          ))}
          {debouncedQuery.length >= 2 && fulltext.data && (
            <span className="ml-auto text-[10px] text-nexus-text-secondary self-center font-mono">
              {results.length} result{results.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto">
          {!debouncedQuery && (
            <div className="px-4 py-8 text-center text-sm text-nexus-text-secondary">
              Type to search entities across all intelligence sources
            </div>
          )}

          {debouncedQuery && results.length === 0 && !isLoading && (
            <div className="px-4 py-8 text-center text-sm text-nexus-text-secondary">
              No entities found for &quot;{debouncedQuery}&quot;
            </div>
          )}

          {results.map((result, idx) => (
            <button
              key={`${result.source}-${result.id}`}
              onClick={() => handleSelect(result.id)}
              onMouseEnter={() => setSelectedIndex(idx)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                idx === selectedIndex
                  ? 'bg-nexus-cyan/10 text-nexus-cyan'
                  : 'text-nexus-text hover:bg-nexus-bg'
              }`}
            >
              {/* Entity icon */}
              <span className="w-6 text-center text-base opacity-70">
                {getEntityIcon(result.type)}
              </span>

              {/* Name + type */}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-mono truncate">{result.name}</div>
                <div className="text-[10px] text-nexus-text-secondary uppercase tracking-wider">
                  {result.type}
                </div>
              </div>

              {/* Score bar */}
              <ConfidenceBar score={result.score > 1 ? result.score / 10 : result.score} />

              {/* Source badge */}
              <span
                className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${
                  result.source === 'semantic'
                    ? 'bg-purple-500/20 text-purple-400'
                    : 'bg-nexus-cyan/20 text-nexus-cyan'
                }`}
              >
                {result.source === 'semantic' ? 'SEM' : 'FT'}
              </span>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-nexus-border text-[10px] text-nexus-text-secondary font-mono">
          <span><kbd className="px-1 py-0.5 rounded bg-nexus-bg border border-nexus-border">{'\u2191\u2193'}</kbd> navigate</span>
          <span><kbd className="px-1 py-0.5 rounded bg-nexus-bg border border-nexus-border">{'\u23CE'}</kbd> select</span>
          <span><kbd className="px-1 py-0.5 rounded bg-nexus-bg border border-nexus-border">esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
