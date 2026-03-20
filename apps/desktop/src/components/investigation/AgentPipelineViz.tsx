interface AgentState {
  name: string;
  status: 'waiting' | 'running' | 'completed' | 'failed';
  itemsProcessed: number;
}

const AGENT_ORDER = ['collector', 'extractor', 'analyst', 'verifier'];

const STATUS_STYLES: Record<string, { border: string; bg: string; text: string; pulse: boolean }> = {
  waiting: { border: 'border-nexus-border', bg: 'bg-transparent', text: 'text-nexus-text-secondary', pulse: false },
  running: { border: 'border-nexus-cyan', bg: 'bg-nexus-cyan/10', text: 'text-nexus-cyan', pulse: true },
  completed: { border: 'border-green-500', bg: 'bg-green-500/10', text: 'text-green-400', pulse: false },
  failed: { border: 'border-red-500', bg: 'bg-red-500/10', text: 'text-red-400', pulse: false },
};

interface AgentPipelineVizProps {
  agents: AgentState[];
}

export function AgentPipelineViz({ agents }: AgentPipelineVizProps) {
  const agentMap = new Map(agents.map((a) => [a.name, a]));

  return (
    <div className="space-y-1">
      <span className="text-[10px] font-mono text-nexus-text-secondary uppercase tracking-wider">
        Pipeline
      </span>

      <div className="space-y-0">
        {AGENT_ORDER.map((name, i) => {
          const agent = agentMap.get(name) || { name, status: 'waiting', itemsProcessed: 0 };
          const style = STATUS_STYLES[agent.status] || STATUS_STYLES.waiting;

          return (
            <div key={name}>
              {/* Agent node */}
              <div
                className={`px-3 py-2 rounded-lg border ${style.border} ${style.bg} transition-all ${
                  style.pulse ? 'animate-pulse' : ''
                }`}
              >
                <div className={`text-xs font-mono capitalize ${style.text}`}>
                  {name}
                </div>
                <div className="text-[10px] font-mono text-nexus-text-secondary mt-0.5">
                  {agent.status}
                </div>
              </div>

              {/* Connector line */}
              {i < AGENT_ORDER.length - 1 && (
                <div className="flex justify-center py-0.5">
                  <div className="w-px h-3 bg-nexus-border" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
