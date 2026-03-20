import { useState } from 'react';
import { investigations } from '@/services/api';
import { joinInvestigation } from '@/services/websocket';

const INT_OPTIONS = ['CYBINT', 'SOCMINT', 'SIGINT', 'GEOINT'] as const;
const PRIORITIES = ['low', 'medium', 'high', 'critical'] as const;

interface InvestigationCreateDialogProps {
  open: boolean;
  onClose: () => void;
}

export function InvestigationCreateDialog({ open, onClose }: InvestigationCreateDialogProps) {
  const [query, setQuery] = useState('');
  const [selectedInts, setSelectedInts] = useState<Set<string>>(new Set(['CYBINT']));
  const [priority, setPriority] = useState<string>('medium');
  const [loading, setLoading] = useState(false);

  const toggleInt = (int: string) => {
    const next = new Set(selectedInts);
    if (next.has(int)) next.delete(int);
    else next.add(int);
    setSelectedInts(next);
  };

  const handleSubmit = async () => {
    if (!query.trim() || selectedInts.size === 0) return;
    setLoading(true);
    try {
      const result = (await investigations.create({
        query: query.trim(),
        target_ints: Array.from(selectedInts),
        priority,
      })) as { id: string };

      // Auto-execute and subscribe
      await investigations.execute(result.id);
      joinInvestigation(result.id);
      onClose();
    } catch (err) {
      console.error('Failed to create investigation:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-nexus-card border border-nexus-border rounded-xl shadow-2xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="px-5 py-4 border-b border-nexus-border">
          <h2 className="text-sm font-heading text-nexus-text-primary">New Investigation</h2>
          <p className="text-[10px] font-mono text-nexus-text-secondary mt-1">
            Configure and launch a multi-INT investigation
          </p>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          {/* Query */}
          <div>
            <label className="text-[10px] font-mono text-nexus-text-secondary uppercase tracking-wider">
              Query / Target
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
              className="w-full mt-1 bg-nexus-bg border border-nexus-border rounded-lg px-3 py-2 text-xs font-mono text-nexus-text-primary placeholder:text-nexus-text-secondary/50 focus:border-nexus-cyan/50 focus:outline-none resize-none"
              placeholder="e.g., 192.168.1.1, example.com, @username, flight AA123..."
            />
          </div>

          {/* INT selection */}
          <div>
            <label className="text-[10px] font-mono text-nexus-text-secondary uppercase tracking-wider">
              Intelligence Sources
            </label>
            <div className="flex gap-2 mt-1">
              {INT_OPTIONS.map((int) => (
                <button
                  key={int}
                  onClick={() => toggleInt(int)}
                  className={`px-3 py-1.5 text-[10px] font-mono rounded-lg border transition-colors ${
                    selectedInts.has(int)
                      ? 'bg-nexus-cyan/10 text-nexus-cyan border-nexus-cyan/40'
                      : 'text-nexus-text-secondary border-nexus-border hover:border-nexus-text-secondary'
                  }`}
                >
                  {int}
                </button>
              ))}
            </div>
          </div>

          {/* Priority */}
          <div>
            <label className="text-[10px] font-mono text-nexus-text-secondary uppercase tracking-wider">
              Priority
            </label>
            <div className="flex gap-2 mt-1">
              {PRIORITIES.map((p) => (
                <button
                  key={p}
                  onClick={() => setPriority(p)}
                  className={`px-3 py-1.5 text-[10px] font-mono rounded-lg border transition-colors capitalize ${
                    priority === p
                      ? 'bg-nexus-cyan/10 text-nexus-cyan border-nexus-cyan/40'
                      : 'text-nexus-text-secondary border-nexus-border hover:border-nexus-text-secondary'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-nexus-border flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-mono text-nexus-text-secondary hover:text-nexus-text-primary transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !query.trim() || selectedInts.size === 0}
            className="px-4 py-1.5 text-xs font-mono bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/40 rounded-lg hover:bg-nexus-cyan/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Launching...' : 'Launch Investigation'}
          </button>
        </div>
      </div>
    </div>
  );
}
