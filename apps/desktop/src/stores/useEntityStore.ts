import { create } from 'zustand';

interface EntityDetail {
  id: string;
  type: string;
  name: string;
  properties: Record<string, unknown>;
  confidence: number;
  sourceInt: string;
  riskScore: number;
  firstSeen: string;
  lastSeen: string;
}

interface Relationship {
  id: string;
  type: string;
  sourceId: string;
  targetId: string;
  confidence: number;
  sourceInt: string;
}

interface TimelineEvent {
  timestamp: string;
  eventType: string;
  title: string;
  description: string;
  sourceInt: string;
  confidence: number;
}

interface EntityState {
  selectedEntity: EntityDetail | null;
  entityRelationships: Relationship[];
  entityTimeline: TimelineEvent[];
  detailPanelOpen: boolean;

  setSelectedEntity: (entity: EntityDetail | null) => void;
  setEntityRelationships: (rels: Relationship[]) => void;
  setEntityTimeline: (events: TimelineEvent[]) => void;
  setDetailPanelOpen: (open: boolean) => void;
  clearSelection: () => void;
}

export const useEntityStore = create<EntityState>((set) => ({
  selectedEntity: null,
  entityRelationships: [],
  entityTimeline: [],
  detailPanelOpen: false,

  setSelectedEntity: (entity) => set({ selectedEntity: entity, detailPanelOpen: !!entity }),
  setEntityRelationships: (rels) => set({ entityRelationships: rels }),
  setEntityTimeline: (events) => set({ entityTimeline: events }),
  setDetailPanelOpen: (open) => set({ detailPanelOpen: open }),
  clearSelection: () =>
    set({
      selectedEntity: null,
      entityRelationships: [],
      entityTimeline: [],
      detailPanelOpen: false,
    }),
}));
