import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '@/stores/useAppStore';
import { useRecentInvestigations } from '@/hooks/useDashboard';
import { useCollectionStore } from '@/stores/useCollectionStore';

const INT_ICONS = [
  { id: 'SOCMINT', label: 'Social', color: 'bg-blue-500', icon: '👤' },
  { id: 'GEOINT', label: 'Geo', color: 'bg-emerald-500', icon: '🌍' },
  { id: 'SIGINT', label: 'Signal', color: 'bg-amber-500', icon: '📡' },
  { id: 'CYBINT', label: 'Cyber', color: 'bg-red-500', icon: '🔒' },
];

const STATUS_DOT: Record<string, string> = {
  completed: 'bg-green-400',
  complete: 'bg-green-400',
  failed: 'bg-red-400',
  collecting: 'bg-blue-400 animate-pulse',
  analyzing: 'bg-yellow-400 animate-pulse',
};

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useAppStore();
  const { data: recentData } = useRecentInvestigations({ limit: 3 });
  const toggleCollection = useCollectionStore((s) => s.togglePanel);

  return (
    <motion.div
      layout
      className={clsx(
        'flex flex-col h-full bg-nexus-bg-secondary border-r border-nexus-border relative z-20',
        sidebarCollapsed ? 'w-12' : 'w-48',
      )}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {/* Toggle */}
      <button
        onClick={toggleSidebar}
        className="h-8 flex items-center justify-center hover:bg-nexus-card transition-colors text-nexus-text-secondary group"
      >
        <span className="text-xs group-hover:text-nexus-cyan transition-colors">{sidebarCollapsed ? '>>' : '<<'}</span>
      </button>

      {/* INT Navigation */}
      <div className="flex flex-col gap-1 p-1">
        {INT_ICONS.map((int) => (
          <motion.button
            whileHover={{ scale: 1.02, x: 2 }}
            whileTap={{ scale: 0.98 }}
            key={int.id}
            className="flex items-center gap-2 px-2 py-2 rounded hover:bg-nexus-card transition-colors group relative overflow-hidden"
            title={int.label}
          >
            <div className={clsx('w-2 h-2 rounded-full shadow-[0_0_8px_currentColor] transition-transform group-hover:scale-125', int.color.replace('bg-', 'text-').replace('-500', '-400'), int.color)} />

            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.span
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="text-xs text-nexus-text-secondary group-hover:text-nexus-text transition-colors"
                >
                  {int.label}
                </motion.span>
              )}
            </AnimatePresence>

            {/* Hover Glow Effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent to-white/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
          </motion.button>
        ))}
      </div>

      {/* Collect Button */}
      <div className="px-1 mt-1">
        <motion.button
          whileHover={{ scale: 1.02, x: 2 }}
          whileTap={{ scale: 0.98 }}
          onClick={toggleCollection}
          className="flex items-center gap-2 px-2 py-2 rounded hover:bg-nexus-card transition-colors group relative overflow-hidden w-full"
          title="OSINT Collection"
        >
          <div className="w-2 h-2 rounded-full bg-nexus-cyan shadow-[0_0_8px_rgba(0,229,255,0.6)] transition-transform group-hover:scale-125" />
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="text-xs text-nexus-cyan group-hover:text-nexus-text transition-colors font-mono uppercase tracking-wider"
              >
                Collect
              </motion.span>
            )}
          </AnimatePresence>
          <div className="absolute inset-0 bg-gradient-to-r from-transparent to-nexus-cyan/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
        </motion.button>
      </div>

      {/* Monitor Button */}
      <div className="px-1 mt-1">
        <motion.button
          whileHover={{ scale: 1.02, x: 2 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => useAppStore.getState().setActiveTab('monitoring')}
          className="flex items-center gap-2 px-2 py-2 rounded hover:bg-nexus-card transition-colors group relative overflow-hidden w-full"
          title="Monitoring Center"
        >
          <div className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)] transition-transform group-hover:scale-125" />
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="text-xs text-amber-400 group-hover:text-nexus-text transition-colors font-mono uppercase tracking-wider"
              >
                Monitor
              </motion.span>
            )}
          </AnimatePresence>
          <div className="absolute inset-0 bg-gradient-to-r from-transparent to-amber-400/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
        </motion.button>
      </div>

      {/* Divider */}
      <div className="mx-2 my-2 border-t border-nexus-border" />

      {/* Investigations section */}
      <AnimatePresence>
        {!sidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex-1 px-2 overflow-hidden"
          >
            <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2">
              Investigations
            </p>
            {recentData?.items && recentData.items.length > 0 ? (
              <div className="space-y-1">
                {recentData.items.map((inv) => (
                  <motion.div
                    whileHover={{ x: 2, backgroundColor: 'rgba(18, 25, 43, 0.8)' }}
                    key={inv.id}
                    className="flex items-center gap-1.5 px-1 py-1 rounded cursor-pointer transition-colors"
                  >
                    <div className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', STATUS_DOT[inv.status] || 'bg-gray-400')} />
                    <span className="text-[10px] font-mono text-nexus-text truncate group-hover:text-nexus-cyan transition-colors">{inv.query}</span>
                  </motion.div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-nexus-text-secondary italic">No active investigations</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Minimap placeholder */}
      <div className="mt-auto p-2">
        <motion.div
          layout
          className={clsx(
            'rounded premium-border glass-panel flex items-center justify-center overflow-hidden relative group cursor-pointer',
            sidebarCollapsed ? 'h-8' : 'h-24',
          )}
        >
          {/* Radar sweep effect */}
          <div className="absolute inset-0 bg-[conic-gradient(from_0deg_at_50%_50%,transparent_0deg,rgba(0,229,255,0.2)_360deg)] animate-[spin_4s_linear_infinite] opacity-50 group-hover:opacity-100 transition-opacity" />

          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[10px] font-mono text-nexus-cyan-muted group-hover:text-nexus-cyan transition-colors relative z-10"
              >
                Minimap Active
              </motion.span>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </motion.div>
  );
}
