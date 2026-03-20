import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { collection } from '@/services/api';

interface PivotNode {
  id: string;
  int_type: string;
  query: string;
  scan_type: string;
  status: string;
  progress: number;
  result_count: number;
  pivot_depth: number;
  pivot_entity_type: string | null;
  parent_job_id: string | null;
  auto_pivot: boolean;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  queued: 'border-gray-400/30 text-gray-400',
  running: 'border-nexus-cyan/30 text-nexus-cyan animate-pulse',
  completed: 'border-green-400/30 text-green-400',
  failed: 'border-red-400/30 text-red-400',
};

const DEPTH_INDENT = 16;

function TreeNode({ node, depth }: { node: PivotNode; depth: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: depth * 0.05 }}
      className={clsx(
        'flex items-center gap-1.5 py-1 px-1.5 rounded border transition-colors',
        STATUS_COLORS[node.status] || STATUS_COLORS.queued,
        'bg-nexus-bg/50'
      )}
      style={{ marginLeft: depth * DEPTH_INDENT }}
    >
      {/* Depth indicator */}
      {depth > 0 && (
        <div className="flex items-center gap-0.5">
          {Array.from({ length: depth }).map((_, i) => (
            <div key={i} className="w-0.5 h-3 bg-nexus-border rounded-full" />
          ))}
          <span className="text-[8px] opacity-50">{'>'}</span>
        </div>
      )}

      {/* Status dot */}
      <div className={clsx(
        'w-2 h-2 rounded-full flex-shrink-0',
        node.status === 'completed' ? 'bg-green-400' :
        node.status === 'running' ? 'bg-nexus-cyan animate-pulse' :
        node.status === 'failed' ? 'bg-red-400' : 'bg-gray-400'
      )} />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1">
          <span className="text-[9px] font-mono truncate">{node.query}</span>
        </div>
        <div className="flex items-center gap-1 mt-0.5">
          <span className="text-[7px] font-mono opacity-70">{node.int_type}</span>
          <span className="text-[7px] font-mono opacity-50">{node.scan_type}</span>
          {node.pivot_entity_type && (
            <span className="text-[7px] font-mono text-amber-400 bg-amber-400/10 px-0.5 rounded">
              {node.pivot_entity_type}
            </span>
          )}
        </div>
      </div>

      {/* Result count */}
      <span className="text-[8px] font-mono opacity-70 flex-shrink-0">
        {node.status === 'completed' ? `${node.result_count}` :
         node.status === 'running' ? `${node.progress}%` : '...'}
      </span>
    </motion.div>
  );
}

export function PivotTreeView({ rootJobId, onClose }: { rootJobId: string; onClose: () => void }) {
  const [nodes, setNodes] = useState<PivotNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    const fetchTree = async () => {
      try {
        const tree = await collection.getTree(rootJobId) as PivotNode[];
        setNodes(tree);
        setError(null);

        // Stop polling if all done
        const allDone = tree.every((n) => n.status === 'completed' || n.status === 'failed');
        if (allDone && interval) clearInterval(interval);
      } catch {
        setError('Failed to load pivot tree');
      } finally {
        setLoading(false);
      }
    };

    fetchTree();
    interval = setInterval(fetchTree, 5000);

    return () => clearInterval(interval);
  }, [rootJobId]);

  const totalResults = nodes.reduce((sum, n) => sum + (n.result_count || 0), 0);
  const completedCount = nodes.filter((n) => n.status === 'completed').length;
  const runningCount = nodes.filter((n) => n.status === 'running' || n.status === 'queued').length;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-2 border-b border-nexus-border bg-nexus-bg/30"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-cyan">
            Pivot Tree
          </p>
          <p className="text-[8px] font-mono text-nexus-text-secondary">
            {completedCount}/{nodes.length} completed
            {runningCount > 0 && ` | ${runningCount} running`}
            {' | '}{totalResults} total results
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-[10px] text-nexus-text-secondary hover:text-nexus-text transition-colors"
        >
          x
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-4">
          <div className="w-4 h-4 border-2 border-nexus-cyan/30 border-t-nexus-cyan rounded-full animate-spin" />
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-[10px] font-mono text-red-400 py-2">{error}</p>
      )}

      {/* Tree */}
      {!loading && !error && (
        <AnimatePresence>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {nodes.map((node) => (
              <TreeNode key={node.id} node={node} depth={node.pivot_depth} />
            ))}
          </div>
        </AnimatePresence>
      )}
    </motion.div>
  );
}
