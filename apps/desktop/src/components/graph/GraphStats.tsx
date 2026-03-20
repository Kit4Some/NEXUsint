import { useGraphStore } from '@/stores/useGraphStore';

export function GraphStats() {
  const { nodes, edges } = useGraphStore();

  return (
    <div className="bg-nexus-card/90 border border-nexus-border rounded px-3 py-1.5 flex gap-4 backdrop-blur-sm">
      <span className="text-[10px] font-mono text-nexus-text-secondary">
        <span className="text-nexus-cyan">{nodes.size}</span> nodes
      </span>
      <span className="text-[10px] font-mono text-nexus-text-secondary">
        <span className="text-nexus-cyan">{edges.size}</span> edges
      </span>
    </div>
  );
}
