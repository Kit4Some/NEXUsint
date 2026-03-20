import { create } from 'zustand';

export type TabId = 'map' | 'graph' | 'timeline' | 'dashboard' | 'report' | 'stix' | 'monitoring';

interface AppState {
  activeTab: TabId;
  sidebarCollapsed: boolean;
  commandPaletteOpen: boolean;
  searchOverlayOpen: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  entityCount: number;
  relationshipCount: number;
  activeCollections: number;
  lastUpdate: string | null;

  setActiveTab: (tab: TabId) => void;
  toggleSidebar: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setSearchOverlayOpen: (open: boolean) => void;
  setConnectionStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;
  setStats: (stats: { entityCount?: number; relationshipCount?: number; activeCollections?: number }) => void;
  setLastUpdate: (time: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeTab: 'map',
  sidebarCollapsed: false,
  commandPaletteOpen: false,
  searchOverlayOpen: false,
  connectionStatus: 'disconnected',
  entityCount: 0,
  relationshipCount: 0,
  activeCollections: 0,
  lastUpdate: null,

  setActiveTab: (tab) => set({ activeTab: tab }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setSearchOverlayOpen: (open) => set({ searchOverlayOpen: open }),
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setStats: (stats) => set((s) => ({ ...s, ...stats })),
  setLastUpdate: (time) => set({ lastUpdate: time }),
}));
