import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import { circular } from 'graphology-layout';

/**
 * Apply ForceAtlas2 layout using graphology-layout-forceatlas2.
 */
export function applyForceLayout(graph: Graph, iterations = 100): void {
  forceAtlas2.assign(graph, {
    iterations,
    settings: {
      gravity: 1,
      scalingRatio: 10,
      strongGravityMode: true,
      barnesHutOptimize: graph.order > 200,
    },
  });
}

/**
 * Apply circular layout.
 */
export function applyCircularLayout(graph: Graph): void {
  circular.assign(graph, { scale: 500 });
}

/**
 * Apply hierarchical layout (top-down BFS from highest-degree node).
 */
export function applyHierarchicalLayout(graph: Graph): void {
  const nodes = graph.nodes();
  if (nodes.length === 0) return;

  // Find root: node with highest degree
  let root = nodes[0];
  let maxDeg = 0;
  nodes.forEach((n) => {
    const deg = graph.degree(n);
    if (deg > maxDeg) {
      maxDeg = deg;
      root = n;
    }
  });

  // BFS to assign levels
  const levels = new Map<string, number>();
  const queue: string[] = [root];
  levels.set(root, 0);

  while (queue.length > 0) {
    const current = queue.shift()!;
    const level = levels.get(current)!;
    graph.neighbors(current).forEach((neighbor) => {
      if (!levels.has(neighbor)) {
        levels.set(neighbor, level + 1);
        queue.push(neighbor);
      }
    });
  }

  // Position nodes by level
  const byLevel = new Map<number, string[]>();
  levels.forEach((level, node) => {
    if (!byLevel.has(level)) byLevel.set(level, []);
    byLevel.get(level)!.push(node);
  });

  const levelSpacing = 120;
  const nodeSpacing = 80;

  byLevel.forEach((nodesAtLevel, level) => {
    const totalWidth = (nodesAtLevel.length - 1) * nodeSpacing;
    nodesAtLevel.forEach((node, i) => {
      graph.setNodeAttribute(node, 'x', i * nodeSpacing - totalWidth / 2);
      graph.setNodeAttribute(node, 'y', level * levelSpacing);
    });
  });

  // Position any unvisited nodes
  let unvisitedIndex = 0;
  nodes.forEach((n) => {
    if (!levels.has(n)) {
      graph.setNodeAttribute(n, 'x', unvisitedIndex * nodeSpacing);
      graph.setNodeAttribute(n, 'y', -levelSpacing);
      unvisitedIndex++;
    }
  });
}

/**
 * Apply geographic layout using lat/lon attributes.
 */
export function applyGeoLayout(graph: Graph, scale = 3): void {
  graph.forEachNode((node, attrs) => {
    const lat = attrs.latitude ?? attrs.lat ?? 0;
    const lon = attrs.longitude ?? attrs.lon ?? 0;
    graph.setNodeAttribute(node, 'x', lon * scale);
    graph.setNodeAttribute(node, 'y', -lat * scale); // Invert Y for screen coords
  });
}
