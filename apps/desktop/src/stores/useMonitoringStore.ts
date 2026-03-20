import { create } from 'zustand';

export interface WatchTarget {
  id: string;
  entityId: string | null;
  entityName: string;
  entityType: string;
  intType: string;
  scanType: string;
  query: string;
  intervalHours: number;
  autoPivot: boolean;
  lastCollectedAt: string | null;
  nextCollectionAt: string;
  active: boolean;
  createdAt: string;
}

export interface Alert {
  id: string;
  entityId: string;
  entityName: string;
  alertType: string;
  severity: string;
  title: string;
  description: string;
  acknowledged?: boolean;
  createdAt: string;
}

interface MonitoringState {
  watchTargets: WatchTarget[];
  alerts: Alert[];
  loading: boolean;

  setWatchTargets: (targets: WatchTarget[]) => void;
  addWatchTarget: (target: WatchTarget) => void;
  removeWatchTarget: (id: string) => void;
  updateWatchTarget: (id: string, updates: Partial<WatchTarget>) => void;

  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
  acknowledgeAlert: (id: string) => void;

  setLoading: (loading: boolean) => void;
}

export const useMonitoringStore = create<MonitoringState>((set) => ({
  watchTargets: [],
  alerts: [],
  loading: false,

  setWatchTargets: (targets) => set({ watchTargets: targets }),
  addWatchTarget: (target) =>
    set((s) => ({ watchTargets: [target, ...s.watchTargets] })),
  removeWatchTarget: (id) =>
    set((s) => ({ watchTargets: s.watchTargets.filter((t) => t.id !== id) })),
  updateWatchTarget: (id, updates) =>
    set((s) => ({
      watchTargets: s.watchTargets.map((t) => (t.id === id ? { ...t, ...updates } : t)),
    })),

  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) =>
    set((s) => ({ alerts: [alert, ...s.alerts].slice(0, 200) })),
  acknowledgeAlert: (id) =>
    set((s) => ({
      alerts: s.alerts.map((a) => (a.id === id ? { ...a, acknowledged: true } : a)),
    })),

  setLoading: (loading) => set({ loading }),
}));
