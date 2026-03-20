import { useCallback } from 'react';
import { useGraphStore } from '@/stores/useGraphStore';
import { entities as entitiesApi } from '@/services/api';

interface GraphContextMenuProps {
  x: number;
  y: number;
  nodeId: string | null;
  edgeId: string | null;
  onClose: () => void;
}

export function GraphContextMenu({ x, y, nodeId, edgeId, onClose }: GraphContextMenuProps) {
  const { setNodes, setEdges, nodes, edges } = useGraphStore();

  const expandNode = useCallback(
    async (depth = 1) => {
      if (!nodeId) return;
      try {
        const data = (await entitiesApi.getGraph(nodeId, depth)) as {
          nodes: Array<{
            id: string;
            type: string;
            name: string;
            confidence: number;
            sourceInt: string;
            riskScore: number;
          }>;
          edges: Array<{
            id: string;
            type: string;
            source_id: string;
            target_id: string;
            confidence: number;
          }>;
        };

        // Merge new nodes with existing
        const existingNodes = Array.from(nodes.values());
        const newNodes = data.nodes
          .filter((n) => !nodes.has(n.id))
          .map((n) => ({
            id: n.id,
            type: n.type,
            name: n.name,
            confidence: n.confidence,
            sourceInt: n.sourceInt,
            riskScore: n.riskScore,
          }));
        setNodes([...existingNodes, ...newNodes]);

        const existingEdges = Array.from(edges.values());
        const newEdges = data.edges
          .filter((e) => !edges.has(e.id))
          .map((e) => ({
            id: e.id,
            type: e.type,
            source: e.source_id,
            target: e.target_id,
            confidence: e.confidence,
          }));
        setEdges([...existingEdges, ...newEdges]);
      } catch {
        // API not ready
      }
      onClose();
    },
    [nodeId, nodes, edges, setNodes, setEdges, onClose],
  );

  const copyId = useCallback(() => {
    if (nodeId) navigator.clipboard.writeText(nodeId);
    onClose();
  }, [nodeId, onClose]);

  return (
    <div
      className="absolute z-50 bg-nexus-card border border-nexus-border rounded-lg shadow-xl py-1 min-w-[160px]"
      style={{ left: x, top: y }}
      onClick={(e) => e.stopPropagation()}
    >
      {nodeId && (
        <>
          <MenuItem label="Expand 1-hop" onClick={() => expandNode(1)} />
          <MenuItem label="Expand 2-hop" onClick={() => expandNode(2)} />
          <div className="border-t border-nexus-border my-1" />
          <MenuItem label="Copy ID" onClick={copyId} />
        </>
      )}
      {edgeId && (
        <MenuItem label="View Edge Details" onClick={onClose} />
      )}
      <MenuItem label="Close" onClick={onClose} />
    </div>
  );
}

function MenuItem({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-1.5 text-xs font-mono text-nexus-text-secondary hover:bg-nexus-border/30 hover:text-nexus-text-primary transition-colors"
    >
      {label}
    </button>
  );
}
