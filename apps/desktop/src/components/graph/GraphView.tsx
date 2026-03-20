import { useCallback, useEffect, useMemo, useRef } from 'react';
import Graph from 'graphology';
import { SigmaContainer, useLoadGraph, useRegisterEvents, useSigma } from '@react-sigma/core';
import '@react-sigma/core/lib/react-sigma.min.css';
import { useGraphStore } from '@/stores/useGraphStore';
import { useEntityStore } from '@/stores/useEntityStore';
import { entities as entitiesApi } from '@/services/api';
import { GraphToolbar } from './GraphToolbar';
import { GraphLegend } from './GraphLegend';
import { GraphStats } from './GraphStats';
import {
  applyForceLayout,
  applyCircularLayout,
  applyHierarchicalLayout,
  applyGeoLayout,
} from './layouts/graphLayouts';

const NODE_COLORS: Record<string, string> = {
  Person: '#0096ff',
  Organization: '#8250ff',
  IPAddress: '#ff3366',
  Domain: '#00ff88',
  ThreatActor: '#ffb800',
  Location: '#00d4ff',
  Aircraft: '#ff6b35',
  Vessel: '#20b2aa',
  SocialAccount: '#e040fb',
  default: '#666666',
};

const COMMUNITY_COLORS = [
  '#ff3366', '#0096ff', '#00ff88', '#ffb800', '#8250ff',
  '#e040fb', '#00d4ff', '#ff6b35', '#20b2aa', '#f4845f',
  '#7b68ee', '#00ced1', '#ff69b4', '#32cd32', '#ffa07a',
];

function GraphLoader() {
  const loadGraph = useLoadGraph();
  const { nodes, edges, layout, colorMode } = useGraphStore();

  useEffect(() => {
    const graph = new Graph();

    nodes.forEach((node) => {
      let color = NODE_COLORS[node.type] || NODE_COLORS.default;
      if (colorMode === 'community' && node.communityId != null) {
        color = COMMUNITY_COLORS[node.communityId % COMMUNITY_COLORS.length];
      }
      graph.addNode(node.id, {
        label: node.name,
        size: Math.max(5, (node.riskScore || 0) * 0.3 + 5),
        color,
        x: node.x ?? Math.random() * 1000,
        y: node.y ?? Math.random() * 1000,
        entityType: node.type,
        sourceInt: node.sourceInt,
      });
    });

    edges.forEach((edge) => {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        try {
          graph.addEdge(edge.source, edge.target, {
            label: edge.type,
            size: Math.max(1, edge.confidence * 3),
            color: `rgba(100, 100, 100, ${edge.confidence * 0.8 + 0.2})`,
          });
        } catch {
          // Skip duplicate edges
        }
      }
    });

    // Apply layout
    if (graph.order > 0) {
      switch (layout) {
        case 'force':
          applyForceLayout(graph);
          break;
        case 'circular':
          applyCircularLayout(graph);
          break;
        case 'hierarchical':
          applyHierarchicalLayout(graph);
          break;
        case 'geo':
          applyGeoLayout(graph);
          break;
      }
    }

    loadGraph(graph);
  }, [loadGraph, nodes, edges, layout, colorMode]);

  return null;
}

function GraphEvents() {
  const registerEvents = useRegisterEvents();
  const sigma = useSigma();
  const { setSelectedNodeId } = useGraphStore();
  const { setSelectedEntity } = useEntityStore();

  useEffect(() => {
    registerEvents({
      clickNode: (event) => {
        const nodeId = event.node;
        setSelectedNodeId(nodeId);

        const attrs = sigma.getGraph().getNodeAttributes(nodeId);
        setSelectedEntity({
          id: nodeId,
          type: attrs.entityType || '',
          name: attrs.label || '',
          properties: {},
          confidence: 0,
          sourceInt: attrs.sourceInt || '',
          riskScore: 0,
          firstSeen: '',
          lastSeen: '',
        });
      },
      clickStage: () => {
        setSelectedNodeId(null);
      },
    });
  }, [registerEvents, sigma, setSelectedNodeId, setSelectedEntity]);

  return null;
}

export function GraphView() {
  const { nodes, setNodes, setEdges, colorMode, setColorMode } = useGraphStore();
  const initialLoadDone = useRef(false);

  // Load graph data on first mount
  useEffect(() => {
    if (initialLoadDone.current || nodes.size > 0) return;
    initialLoadDone.current = true;

    (async () => {
      try {
        // First fetch entities to find a center node
        const data = (await entitiesApi.search({ limit: 100 })) as Array<{
          id: string;
          type: string;
          name: string;
          confidence: number;
          source_int: string;
          risk_score: number;
        }>;

        if (data.length === 0) return;

        // Use first entity to fetch a connected subgraph with edges
        const subgraph = (await entitiesApi.getGraph(data[0].id, 3)) as {
          nodes: Array<{
            id: string;
            type: string;
            name: string;
            confidence: number;
            source_int: string;
            risk_score: number;
          }>;
          edges: Array<{
            id: string;
            type: string;
            source_id: string;
            target_id: string;
            confidence: number;
          }>;
        };

        if (subgraph.nodes?.length > 0) {
          setNodes(
            subgraph.nodes.map((e) => ({
              id: e.id,
              type: e.type,
              name: e.name,
              confidence: e.confidence,
              sourceInt: e.source_int,
              riskScore: e.risk_score,
            })),
          );
        }

        if (subgraph.edges?.length > 0) {
          setEdges(
            subgraph.edges.map((e) => ({
              id: e.id,
              type: e.type,
              source: e.source_id,
              target: e.target_id,
              confidence: e.confidence ?? 0.5,
            })),
          );
        }
      } catch (err) {
        console.error('[Graph] Entity fetch failed:', err);
      }
    })();
  }, [nodes.size, setNodes, setEdges]);

  return (
    <div className="relative w-full h-full bg-nexus-bg">
      <SigmaContainer
        style={{ width: '100%', height: '100%' }}
        settings={{
          renderEdgeLabels: true,
          defaultEdgeType: 'arrow',
          defaultNodeColor: '#666',
          labelColor: { color: '#c0c0c0' },
          labelSize: 11,
          labelRenderedSizeThreshold: 8,
        }}
      >
        <GraphLoader />
        <GraphEvents />
      </SigmaContainer>

      <div className="absolute top-3 left-3 flex gap-2">
        <GraphToolbar />
        <button
          onClick={() => setColorMode(colorMode === 'type' ? 'community' : 'type')}
          className={`px-2 py-1 rounded text-[9px] font-mono border transition-colors ${
            colorMode === 'community'
              ? 'text-nexus-cyan border-nexus-cyan/40 bg-nexus-cyan/10'
              : 'text-nexus-text-secondary border-nexus-border hover:border-nexus-text-secondary'
          }`}
          title="Toggle between entity type and community coloring"
        >
          {colorMode === 'community' ? 'Community Colors' : 'Type Colors'}
        </button>
      </div>

      <div className="absolute top-3 right-3">
        <GraphLegend />
      </div>

      <div className="absolute bottom-3 left-3">
        <GraphStats />
      </div>
    </div>
  );
}
