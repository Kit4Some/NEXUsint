import { useState } from 'react';
import { useRecentInvestigations } from '@/hooks/useDashboard';

interface InvestigationListProps {
  onSelect: (id: string) => void;
}

const STATUS_FILTERS = ['all', 'created', 'collecting', 'analyzing', 'completed', 'failed'] as const;

const STATUS_COLORS: Record<string, string> = {
  created: 'bg-gray-500/20 text-gray-400',
  collecting: 'bg-blue-500/20 text-blue-400',
  extracting: 'bg-purple-500/20 text-purple-400',
  analyzing: 'bg-yellow-500/20 text-yellow-400',
  verifying: 'bg-orange-500/20 text-orange-400',
  completed: 'bg-green-500/20 text-green-400',
  complete: 'bg-green-500/20 text-green-400',
  failed: 'bg-red-500/20 text-red-400',
};

export function InvestigationList({ onSelect }: InvestigationListProps) {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const { data, isLoading } = useRecentInvestigations({
    status: statusFilter === 'all' ? undefined : statusFilter,
    limit: pageSize,
    offset: page * pageSize,
  });

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / pageSize);

  const filtered = searchQuery
    ? items.filter((inv) => inv.query.toLowerCase().includes(searchQuery.toLowerCase()))
    : items;

  return (
    <div className="h-full flex flex-col bg-nexus-bg">
      {/* Header */}
      <div className="px-4 py-3 border-b border-nexus-border space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-heading text-nexus-text-primary">Investigations</h3>
          <span className="text-[10px] font-mono text-nexus-text-secondary">{total} total</span>
        </div>

        {/* Search */}
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter investigations..."
          className="w-full px-2 py-1.5 text-xs font-mono bg-nexus-bg border border-nexus-border rounded outline-none text-nexus-text placeholder:text-nexus-text-secondary focus:border-nexus-cyan/50"
        />

        {/* Status filters */}
        <div className="flex gap-1 flex-wrap">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(0); }}
              className={`text-[9px] font-mono px-2 py-0.5 rounded transition-colors ${
                statusFilter === s
                  ? 'bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/30'
                  : 'text-nexus-text-secondary hover:text-nexus-text hover:bg-nexus-card'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center h-32 text-xs font-mono text-nexus-text-secondary">
            Loading...
          </div>
        )}

        {!isLoading && filtered.map((inv) => (
          <div
            key={inv.id}
            onClick={() => onSelect(inv.id)}
            className="px-4 py-3 border-b border-nexus-border/50 hover:bg-nexus-card/30 cursor-pointer transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-nexus-text-primary truncate max-w-[200px]">
                {inv.query}
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${STATUS_COLORS[inv.status] || 'bg-gray-500/20 text-gray-400'}`}>
                {inv.status}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-[10px] font-mono text-nexus-text-secondary">
              <span>{inv.entity_count} entities</span>
              <span>{inv.priority}</span>
              <span>{new Date(inv.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}

        {!isLoading && filtered.length === 0 && (
          <div className="flex items-center justify-center h-32 text-xs font-mono text-nexus-text-secondary">
            No investigations found
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-4 py-2 border-t border-nexus-border flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="text-[10px] font-mono text-nexus-text-secondary hover:text-nexus-cyan disabled:opacity-30"
          >
            Prev
          </button>
          <span className="text-[10px] font-mono text-nexus-text-secondary">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="text-[10px] font-mono text-nexus-text-secondary hover:text-nexus-cyan disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
