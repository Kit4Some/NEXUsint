import { create } from 'zustand';

export type IntType = 'cybint' | 'socmint' | 'sigint' | 'geoint';

interface CollectionJob {
  id: string;
  intType: IntType;
  query: string;
  scanType: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  resultCount: number;
  error?: string;
  createdAt: string;
}

interface PivotChild {
  parentJobId: string;
  childJobId: string;
  entityType: string;
  entityName: string;
  scanType: string;
  intType: string;
  pivotDepth: number;
}

export interface HistoryJob {
  id: string;
  int_type: string;
  query: string;
  scan_type: string;
  status: string;
  progress: number;
  result_count: number;
  error: string | null;
  parent_job_id: string | null;
  pivot_depth: number;
  auto_pivot: boolean;
  created_at: string | null;
  completed_at: string | null;
}

interface CollectionState {
  isOpen: boolean;
  activeTab: 'active' | 'history';
  activeJobs: Map<string, CollectionJob>;
  recentEntities: Array<{ id: string; type: string; name: string; confidence: number; sourceInt: string }>;
  pivotChildren: Map<string, PivotChild[]>;
  historyJobs: HistoryJob[];
  historyTotal: number;
  selectedJobEntities: Array<{ id: string; name: string; type: string; confidence: number; sourceInt: string; riskScore: number }>;

  togglePanel: () => void;
  setOpen: (open: boolean) => void;
  setActiveTab: (tab: 'active' | 'history') => void;
  addJob: (job: CollectionJob) => void;
  updateJob: (jobId: string, updates: Partial<CollectionJob>) => void;
  removeJob: (jobId: string) => void;
  addRecentEntity: (entity: { id: string; type: string; name: string; confidence: number; sourceInt: string }) => void;
  addPivotChild: (parentJobId: string, child: PivotChild) => void;
  setHistoryJobs: (jobs: HistoryJob[], total: number) => void;
  setSelectedJobEntities: (entities: Array<{ id: string; name: string; type: string; confidence: number; sourceInt: string; riskScore: number }>) => void;
}

export const useCollectionStore = create<CollectionState>((set) => ({
  isOpen: false,
  activeTab: 'active',
  activeJobs: new Map(),
  recentEntities: [],
  pivotChildren: new Map(),
  historyJobs: [],
  historyTotal: 0,
  selectedJobEntities: [],

  togglePanel: () => set((s) => ({ isOpen: !s.isOpen })),
  setOpen: (open) => set({ isOpen: open }),
  setActiveTab: (activeTab) => set({ activeTab }),

  addJob: (job) =>
    set((s) => {
      const jobs = new Map(s.activeJobs);
      jobs.set(job.id, job);
      return { activeJobs: jobs };
    }),

  updateJob: (jobId, updates) =>
    set((s) => {
      const jobs = new Map(s.activeJobs);
      const existing = jobs.get(jobId);
      if (existing) {
        jobs.set(jobId, { ...existing, ...updates });
      }
      return { activeJobs: jobs };
    }),

  removeJob: (jobId) =>
    set((s) => {
      const jobs = new Map(s.activeJobs);
      jobs.delete(jobId);
      return { activeJobs: jobs };
    }),

  addRecentEntity: (entity) =>
    set((s) => ({
      recentEntities: [entity, ...s.recentEntities].slice(0, 50),
    })),

  addPivotChild: (parentJobId, child) =>
    set((s) => {
      const pivots = new Map(s.pivotChildren);
      const existing = pivots.get(parentJobId) || [];
      pivots.set(parentJobId, [...existing, child]);
      return { pivotChildren: pivots };
    }),

  setHistoryJobs: (jobs, total) => set({ historyJobs: jobs, historyTotal: total }),
  setSelectedJobEntities: (entities) => set({ selectedJobEntities: entities }),
}));
