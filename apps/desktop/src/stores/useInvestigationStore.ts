import { create } from 'zustand';

interface AgentState {
  name: string;
  status: 'waiting' | 'running' | 'completed' | 'failed';
  itemsProcessed: number;
}

interface LogEntry {
  timestamp: string;
  level: string;
  agent: string;
  message: string;
}

interface InvestigationState {
  currentInvestigationId: string | null;
  status: string;
  progress: number;
  agentStates: AgentState[];
  discoveredEntities: Array<{ id: string; type: string; name: string; confidence: number }>;
  liveLog: LogEntry[];

  setCurrentInvestigation: (id: string | null) => void;
  setStatus: (status: string) => void;
  setProgress: (progress: number) => void;
  updateAgentState: (agent: AgentState) => void;
  addDiscoveredEntity: (entity: { id: string; type: string; name: string; confidence: number }) => void;
  addLogEntry: (entry: LogEntry) => void;
  reset: () => void;
}

export const useInvestigationStore = create<InvestigationState>((set) => ({
  currentInvestigationId: null,
  status: 'idle',
  progress: 0,
  agentStates: [
    { name: 'collector', status: 'waiting', itemsProcessed: 0 },
    { name: 'extractor', status: 'waiting', itemsProcessed: 0 },
    { name: 'analyst', status: 'waiting', itemsProcessed: 0 },
    { name: 'verifier', status: 'waiting', itemsProcessed: 0 },
  ],
  discoveredEntities: [],
  liveLog: [],

  setCurrentInvestigation: (id) => set({ currentInvestigationId: id }),
  setStatus: (status) => set({ status }),
  setProgress: (progress) => set({ progress }),
  updateAgentState: (agent) =>
    set((s) => ({
      agentStates: s.agentStates.map((a) => (a.name === agent.name ? agent : a)),
    })),
  addDiscoveredEntity: (entity) =>
    set((s) => ({ discoveredEntities: [...s.discoveredEntities, entity] })),
  addLogEntry: (entry) =>
    set((s) => ({ liveLog: [entry, ...s.liveLog].slice(0, 500) })),
  reset: () =>
    set({
      currentInvestigationId: null,
      status: 'idle',
      progress: 0,
      agentStates: [
        { name: 'collector', status: 'waiting', itemsProcessed: 0 },
        { name: 'extractor', status: 'waiting', itemsProcessed: 0 },
        { name: 'analyst', status: 'waiting', itemsProcessed: 0 },
        { name: 'verifier', status: 'waiting', itemsProcessed: 0 },
      ],
      discoveredEntities: [],
      liveLog: [],
    }),
}));
