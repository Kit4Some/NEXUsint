import { useState } from 'react';
import { useEntityStore } from '@/stores/useEntityStore';
import { useEntityTimeline } from '@/hooks/useTimeline';

interface TimelineEvent {
  timestamp: string;
  event_type: string;
  title: string;
  description: string;
  source_int: string;
  confidence: number;
  entity_id?: string;
}

const INT_COLORS: Record<string, string> = {
  CYBINT: 'bg-red-500/20 text-red-400',
  SOCMINT: 'bg-purple-500/20 text-purple-400',
  SIGINT: 'bg-orange-500/20 text-orange-400',
  GEOINT: 'bg-green-500/20 text-green-400',
};

const EVENT_ICONS: Record<string, string> = {
  RESOLVES_TO: 'dns',
  COMMUNICATES_WITH: 'msg',
  TARGETS: 'tgt',
  AFFILIATED_WITH: 'aff',
  LOCATED_AT: 'loc',
  HOSTS: 'hst',
  SAME_AS: 'dup',
};

export function TimelineView() {
  const { selectedEntity } = useEntityStore();
  const { data, isLoading } = useEntityTimeline(selectedEntity?.id ?? null);
  const [filter, setFilter] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const events = (data as TimelineEvent[] | undefined) ?? [];
  const filtered = events.filter((e) => {
    if (filter && e.source_int !== filter) return false;
    if (dateFrom && e.timestamp && new Date(e.timestamp) < new Date(dateFrom)) return false;
    if (dateTo && e.timestamp && new Date(e.timestamp) > new Date(dateTo + 'T23:59:59')) return false;
    return true;
  });

  if (!selectedEntity) {
    return (
      <div className="flex items-center justify-center h-full text-nexus-text-secondary">
        <div className="text-center">
          <p className="text-sm font-heading">Timeline</p>
          <p className="text-xs font-mono mt-1">Select an entity to view its timeline</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-nexus-bg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-nexus-border">
        <h3 className="text-xs font-heading text-nexus-text-primary">
          Timeline: {selectedEntity.name}
        </h3>

        {/* Filter pills */}
        <div className="flex gap-1 mt-2">
          <FilterPill label="All" active={!filter} onClick={() => setFilter(null)} />
          {Object.keys(INT_COLORS).map((int) => (
            <FilterPill
              key={int}
              label={int}
              active={filter === int}
              onClick={() => setFilter(filter === int ? null : int)}
            />
          ))}
        </div>

        {/* Date range filter */}
        <div className="flex items-center gap-2 mt-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-2 py-0.5 text-[10px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text outline-none focus:border-nexus-cyan/50"
          />
          <span className="text-[10px] text-nexus-text-secondary">to</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-2 py-0.5 text-[10px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text outline-none focus:border-nexus-cyan/50"
          />
          {(dateFrom || dateTo) && (
            <button
              onClick={() => { setDateFrom(''); setDateTo(''); }}
              className="text-[9px] text-nexus-text-secondary hover:text-nexus-text"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {isLoading && (
          <div className="text-xs font-mono text-nexus-text-secondary animate-pulse">Loading...</div>
        )}

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[7px] top-0 bottom-0 w-px bg-nexus-border" />

          {filtered.map((event, i) => (
            <div key={i} className="relative flex gap-3 pb-4">
              {/* Dot */}
              <div className="relative z-10 w-[15px] flex-shrink-0 flex items-start pt-1">
                <div className="w-[15px] h-[15px] rounded-full bg-nexus-card border-2 border-nexus-cyan flex items-center justify-center">
                  <div className="w-[5px] h-[5px] rounded-full bg-nexus-cyan" />
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 bg-nexus-card/50 border border-nexus-border/50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-nexus-text-secondary">
                    {event.timestamp
                      ? new Date(event.timestamp).toLocaleString()
                      : 'Unknown time'}
                  </span>
                  <span className="text-[10px] font-mono text-nexus-cyan">
                    {EVENT_ICONS[event.event_type] || event.event_type}
                  </span>
                  {event.source_int && (
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                        INT_COLORS[event.source_int] || 'bg-gray-500/20 text-gray-400'
                      }`}
                    >
                      {event.source_int}
                    </span>
                  )}
                </div>
                <div className="text-xs font-mono text-nexus-text-primary mt-1">
                  {event.title}
                </div>
                {event.description && (
                  <div className="text-[10px] font-mono text-nexus-text-secondary mt-0.5">
                    {event.description}
                  </div>
                )}
              </div>
            </div>
          ))}

          {filtered.length === 0 && !isLoading && (
            <div className="text-xs font-mono text-nexus-text-secondary text-center py-8">
              No timeline events
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FilterPill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-2 py-0.5 text-[10px] font-mono rounded transition-colors ${
        active
          ? 'bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/40'
          : 'text-nexus-text-secondary hover:text-nexus-text-primary border border-transparent'
      }`}
    >
      {label}
    </button>
  );
}
