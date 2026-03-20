import { useInvestigationStore } from '@/stores/useInvestigationStore';
import { AgentPipelineViz } from './AgentPipelineViz';

export function InvestigationMonitor() {
  const { activeInvestigation, progress, agentStates, discoveredEntities, logEntries } =
    useInvestigationStore();

  if (!activeInvestigation) return null;

  return (
    <div className="h-full flex flex-col bg-nexus-bg overflow-hidden">
      {/* Header bar with progress */}
      <div className="px-4 py-3 border-b border-nexus-border">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-heading text-nexus-text-primary">Investigation Monitor</h3>
            <p className="text-[10px] font-mono text-nexus-text-secondary mt-0.5 truncate max-w-md">
              {activeInvestigation}
            </p>
          </div>
          <span className="text-xs font-mono text-nexus-cyan">{progress}%</span>
        </div>

        {/* Progress bar */}
        <div className="mt-2 w-full h-1 bg-nexus-border rounded-full overflow-hidden">
          <div
            className="h-full bg-nexus-cyan transition-all duration-500 rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* 3-column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Agent pipeline */}
        <div className="w-48 border-r border-nexus-border p-3 overflow-y-auto">
          <AgentPipelineViz agents={agentStates} />
        </div>

        {/* Center: Discovered entities */}
        <div className="flex-1 border-r border-nexus-border overflow-y-auto">
          <div className="px-3 py-2 border-b border-nexus-border/50 sticky top-0 bg-nexus-bg">
            <span className="text-[10px] font-mono text-nexus-text-secondary uppercase tracking-wider">
              Discovered Entities ({discoveredEntities.length})
            </span>
          </div>
          <div className="divide-y divide-nexus-border/30">
            {discoveredEntities.map((ent, i) => (
              <div key={i} className="px-3 py-1.5 hover:bg-nexus-card/30 transition-colors">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{
                      backgroundColor:
                        ent.type === 'IPAddress' ? '#ff3366' :
                        ent.type === 'Domain' ? '#00ff88' :
                        ent.type === 'Person' ? '#0096ff' : '#666',
                    }}
                  />
                  <span className="text-xs font-mono text-nexus-text-primary truncate">
                    {ent.name}
                  </span>
                  <span className="text-[10px] font-mono text-nexus-text-secondary ml-auto">
                    {ent.type}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Log */}
        <div className="w-64 overflow-y-auto">
          <div className="px-3 py-2 border-b border-nexus-border/50 sticky top-0 bg-nexus-bg">
            <span className="text-[10px] font-mono text-nexus-text-secondary uppercase tracking-wider">
              Live Log
            </span>
          </div>
          <div className="p-2 space-y-1">
            {logEntries.map((entry, i) => (
              <div key={i} className="text-[10px] font-mono leading-tight">
                <span className="text-nexus-text-secondary">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>{' '}
                <span className="text-nexus-cyan">[{entry.agent}]</span>{' '}
                <span className="text-nexus-text-primary">{entry.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
