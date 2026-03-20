import { useGraphStore } from '@/stores/useGraphStore';

const LAYOUTS = [
  { id: 'force' as const, label: 'Force' },
  { id: 'hierarchical' as const, label: 'Tree' },
  { id: 'circular' as const, label: 'Circular' },
  { id: 'geo' as const, label: 'Geo' },
];

export function GraphToolbar() {
  const { layout, setLayout, clearGraph, nodes } = useGraphStore();

  return (
    <div className="bg-nexus-card/90 border border-nexus-border rounded-lg p-2 space-y-2 backdrop-blur-sm">
      {/* Layout selector */}
      <div className="flex gap-1">
        {LAYOUTS.map((l) => (
          <button
            key={l.id}
            onClick={() => setLayout(l.id)}
            className={`px-2 py-1 text-[10px] font-mono rounded transition-colors ${
              layout === l.id
                ? 'bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/40'
                : 'text-nexus-text-secondary hover:text-nexus-text-primary hover:bg-nexus-border/30'
            }`}
          >
            {l.label}
          </button>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-1">
        <button
          onClick={clearGraph}
          className="px-2 py-1 text-[10px] font-mono text-nexus-text-secondary hover:text-nexus-red transition-colors"
        >
          Clear
        </button>
        <span className="text-[10px] font-mono text-nexus-text-secondary ml-auto">
          {nodes.size} nodes
        </span>
      </div>
    </div>
  );
}
