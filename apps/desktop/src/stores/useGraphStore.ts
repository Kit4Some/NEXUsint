import { create } from 'zustand';

interface GraphNode {
  id: string;
  type: string;
  name: string;
  confidence: number;
  sourceInt: string;
  riskScore: number;
  communityId?: number;
  x?: number;
  y?: number;
}

interface GraphEdge {
  id: string;
  type: string;
  source: string;
  target: string;
  confidence: number;
}

type LayoutMode = 'force' | 'hierarchical' | 'circular' | 'geo';
type ColorMode = 'type' | 'community';

interface GraphState {
  nodes: Map<string, GraphNode>;
  edges: Map<string, GraphEdge>;
  selectedNodeId: string | null;
  layout: LayoutMode;
  colorMode: ColorMode;

  setNodes: (nodes: GraphNode[]) => void;
  setEdges: (edges: GraphEdge[]) => void;
  setSelectedNodeId: (id: string | null) => void;
  setLayout: (layout: LayoutMode) => void;
  setColorMode: (mode: ColorMode) => void;
  clearGraph: () => void;
}

export const useGraphStore = create<GraphState>((set) => ({
  nodes: new Map(),
  edges: new Map(),
  selectedNodeId: null,
  layout: 'force',
  colorMode: 'type',

  setNodes: (nodes) =>
    set({ nodes: new Map(nodes.map((n) => [n.id, n])) }),
  setEdges: (edges) =>
    set({ edges: new Map(edges.map((e) => [e.id, e])) }),
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  setLayout: (layout) => set({ layout }),
  setColorMode: (colorMode) => set({ colorMode }),
  clearGraph: () => set({ nodes: new Map(), edges: new Map(), selectedNodeId: null }),
}));
