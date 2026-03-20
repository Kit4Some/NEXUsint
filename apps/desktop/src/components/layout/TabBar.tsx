import { clsx } from 'clsx';
import { useAppStore, type TabId } from '@/stores/useAppStore';

const TABS: { id: TabId; label: string; shortcut: string }[] = [
  { id: 'map', label: 'Map', shortcut: 'Ctrl+Shift+M' },
  { id: 'graph', label: 'Graph', shortcut: 'Ctrl+Shift+G' },
  { id: 'timeline', label: 'Timeline', shortcut: '' },
  { id: 'dashboard', label: 'Dashboard', shortcut: 'Ctrl+Shift+D' },
  { id: 'report', label: 'Report', shortcut: '' },
  { id: 'stix', label: 'STIX', shortcut: '' },
  { id: 'monitoring', label: 'Monitor', shortcut: '' },
];

export function TabBar() {
  const { activeTab, setActiveTab } = useAppStore();

  return (
    <div className="flex items-center h-9 bg-nexus-bg-secondary border-b border-nexus-border px-2 gap-1">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          className={clsx(
            'px-3 py-1.5 text-xs font-medium rounded transition-colors relative',
            activeTab === tab.id
              ? 'text-nexus-cyan bg-nexus-card'
              : 'text-nexus-text-secondary hover:text-nexus-text hover:bg-nexus-card/50',
          )}
          title={tab.shortcut}
        >
          {tab.label}
          {activeTab === tab.id && (
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 bg-nexus-cyan rounded-full" />
          )}
        </button>
      ))}

      {/* Spacer + Search trigger */}
      <div className="flex-1" />
      <button
        onClick={() => useAppStore.getState().setCommandPaletteOpen(true)}
        className="flex items-center gap-1.5 px-2 py-1 text-xs text-nexus-text-secondary hover:text-nexus-text border border-nexus-border rounded transition-colors"
      >
        <span>Search</span>
        <kbd className="text-[10px] px-1 py-0.5 rounded bg-nexus-bg border border-nexus-border font-mono">
          Ctrl+K
        </kbd>
      </button>
    </div>
  );
}
