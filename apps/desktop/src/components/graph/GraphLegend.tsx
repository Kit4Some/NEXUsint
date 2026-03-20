import { useState } from 'react';

const LEGEND_ITEMS = [
  { type: 'Person', color: '#0096ff' },
  { type: 'Organization', color: '#8250ff' },
  { type: 'IPAddress', color: '#ff3366' },
  { type: 'Domain', color: '#00ff88' },
  { type: 'ThreatActor', color: '#ffb800' },
  { type: 'Location', color: '#00d4ff' },
  { type: 'Aircraft', color: '#ff6b35' },
  { type: 'Vessel', color: '#20b2aa' },
  { type: 'SocialAccount', color: '#e040fb' },
];

export function GraphLegend() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="bg-nexus-card/90 border border-nexus-border rounded-lg backdrop-blur-sm">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full px-3 py-1.5 text-[10px] font-mono text-nexus-text-secondary text-left hover:text-nexus-text-primary transition-colors"
      >
        Legend {collapsed ? '+' : '-'}
      </button>

      {!collapsed && (
        <div className="px-3 pb-2 space-y-1">
          {LEGEND_ITEMS.map((item) => (
            <div key={item.type} className="flex items-center gap-2">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-[10px] font-mono text-nexus-text-secondary">
                {item.type}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
