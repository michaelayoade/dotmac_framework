/**
 * Network topology utilities
 * Helper functions for topology manipulation and analysis
 */

import type { NetworkNode, NetworkLink, LayoutOptions } from '../types';

export const topologyUtils = {
  /**
   * Find shortest path between nodes using BFS
   */
  findShortestPath: (
    nodes: NetworkNode[],
    links: NetworkLink[],
    sourceId: string,
    targetId: string
  ): string[] => {
    if (sourceId === targetId) return [sourceId];

    // Build adjacency list
    const adjacency: { [nodeId: string]: string[] } = {};
    nodes.forEach((node) => (adjacency[node.node_id] = []));

    links.forEach((link) => {
      if (link.status === 'active') {
        adjacency[link.source_node_id]?.push(link.target_node_id);
        adjacency[link.target_node_id]?.push(link.source_node_id);
      }
    });

    // BFS
    const visited = new Set<string>();
    const queue: { nodeId: string; path: string[] }[] = [{ nodeId: sourceId, path: [sourceId] }];

    while (queue.length > 0) {
      const { nodeId, path } = queue.shift()!;

      if (visited.has(nodeId)) continue;
      visited.add(nodeId);

      if (nodeId === targetId) return path;

      for (const neighbor of adjacency[nodeId] || []) {
        if (!visited.has(neighbor)) {
          queue.push({ nodeId: neighbor, path: [...path, neighbor] });
        }
      }
    }

    return []; // No path found
  },

  /**
   * Calculate node positions for different layouts
   */
  calculateLayout: (
    nodes: NetworkNode[],
    links: NetworkLink[],
    layout: LayoutOptions,
    width: number,
    height: number
  ): { [nodeId: string]: { x: number; y: number } } => {
    const positions: { [nodeId: string]: { x: number; y: number } } = {};

    switch (layout.algorithm) {
      case 'grid':
        return topologyUtils.gridLayout(nodes, width, height);

      case 'circular':
        return topologyUtils.circularLayout(nodes, width, height);

      case 'hierarchical':
        return topologyUtils.hierarchicalLayout(nodes, links, width, height);

      default:
        // Random layout as fallback
        nodes.forEach((node) => {
          positions[node.node_id] = {
            x: Math.random() * width,
            y: Math.random() * height,
          };
        });
        return positions;
    }
  },

  /**
   * Grid layout algorithm
   */
  gridLayout: (nodes: NetworkNode[], width: number, height: number) => {
    const positions: { [nodeId: string]: { x: number; y: number } } = {};
    const cols = Math.ceil(Math.sqrt(nodes.length));
    const cellWidth = width / cols;
    const cellHeight = height / Math.ceil(nodes.length / cols);

    nodes.forEach((node, index) => {
      const row = Math.floor(index / cols);
      const col = index % cols;
      positions[node.node_id] = {
        x: col * cellWidth + cellWidth / 2,
        y: row * cellHeight + cellHeight / 2,
      };
    });

    return positions;
  },

  /**
   * Circular layout algorithm
   */
  circularLayout: (nodes: NetworkNode[], width: number, height: number) => {
    const positions: { [nodeId: string]: { x: number; y: number } } = {};
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 3;

    nodes.forEach((node, index) => {
      const angle = (index / nodes.length) * 2 * Math.PI;
      positions[node.node_id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    return positions;
  },

  /**
   * Hierarchical layout algorithm (simplified)
   */
  hierarchicalLayout: (
    nodes: NetworkNode[],
    links: NetworkLink[],
    width: number,
    height: number
  ) => {
    const positions: { [nodeId: string]: { x: number; y: number } } = {};

    // Group nodes by type hierarchy
    const hierarchy = [
      'core_router',
      'distribution_router',
      'access_switch',
      'wifi_ap',
      'customer_premises',
    ];

    const levels: { [level: number]: NetworkNode[] } = {};

    nodes.forEach((node) => {
      const level = hierarchy.indexOf(node.node_type);
      if (!levels[level]) levels[level] = [];
      levels[level].push(node);
    });

    const levelCount = Object.keys(levels).length;
    const levelHeight = height / Math.max(levelCount, 1);

    Object.entries(levels).forEach(([levelStr, levelNodes]) => {
      const level = parseInt(levelStr);
      const nodeWidth = width / Math.max(levelNodes.length, 1);

      levelNodes.forEach((node, index) => {
        positions[node.node_id] = {
          x: index * nodeWidth + nodeWidth / 2,
          y: level * levelHeight + levelHeight / 2,
        };
      });
    });

    return positions;
  },

  /**
   * Filter topology data based on criteria
   */
  filterTopology: (
    nodes: NetworkNode[],
    links: NetworkLink[],
    filters: {
      nodeTypes?: string[];
      status?: string[];
      searchQuery?: string;
    }
  ): { nodes: NetworkNode[]; links: NetworkLink[] } => {
    let filteredNodes = [...nodes];

    // Filter by node type
    if (filters.nodeTypes && filters.nodeTypes.length > 0) {
      filteredNodes = filteredNodes.filter((node) => filters.nodeTypes!.includes(node.node_type));
    }

    // Filter by status
    if (filters.status && filters.status.length > 0) {
      filteredNodes = filteredNodes.filter((node) => filters.status!.includes(node.status));
    }

    // Filter by search query
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      filteredNodes = filteredNodes.filter(
        (node) =>
          node.name.toLowerCase().includes(query) ||
          node.hostname?.toLowerCase().includes(query) ||
          node.ip_address?.toLowerCase().includes(query)
      );
    }

    // Filter links to only include those connecting filtered nodes
    const nodeIds = new Set(filteredNodes.map((node) => node.node_id));
    const filteredLinks = links.filter(
      (link) => nodeIds.has(link.source_node_id) && nodeIds.has(link.target_node_id)
    );

    return { nodes: filteredNodes, links: filteredLinks };
  },

  /**
   * Calculate topology statistics
   */
  calculateStatistics: (nodes: NetworkNode[], links: NetworkLink[]) => {
    const activeNodes = nodes.filter((node) => node.status === 'active');
    const activeLinks = links.filter((link) => link.status === 'active');

    const nodesByType = nodes.reduce(
      (acc, node) => {
        acc[node.node_type] = (acc[node.node_type] || 0) + 1;
        return acc;
      },
      {} as { [type: string]: number }
    );

    const linksByType = links.reduce(
      (acc, link) => {
        acc[link.link_type] = (acc[link.link_type] || 0) + 1;
        return acc;
      },
      {} as { [type: string]: number }
    );

    const avgConnections =
      nodes.length > 0
        ? nodes.reduce((sum, node) => sum + node.connected_links.length, 0) / nodes.length
        : 0;

    return {
      total_nodes: nodes.length,
      active_nodes: activeNodes.length,
      total_links: links.length,
      active_links: activeLinks.length,
      nodes_by_type: nodesByType,
      links_by_type: linksByType,
      average_connections: avgConnections,
      network_density:
        nodes.length > 1 ? (2 * links.length) / (nodes.length * (nodes.length - 1)) : 0,
    };
  },

  /**
   * Validate topology data integrity
   */
  validateTopology: (
    nodes: NetworkNode[],
    links: NetworkLink[]
  ): {
    valid: boolean;
    errors: string[];
  } => {
    const errors: string[] = [];
    const nodeIds = new Set(nodes.map((node) => node.node_id));

    // Check for orphaned links
    links.forEach((link) => {
      if (!nodeIds.has(link.source_node_id)) {
        errors.push(
          `Link ${link.link_id} references non-existent source node ${link.source_node_id}`
        );
      }
      if (!nodeIds.has(link.target_node_id)) {
        errors.push(
          `Link ${link.link_id} references non-existent target node ${link.target_node_id}`
        );
      }
    });

    // Check for duplicate node IDs
    const nodeIdCounts = new Map<string, number>();
    nodes.forEach((node) => {
      nodeIdCounts.set(node.node_id, (nodeIdCounts.get(node.node_id) || 0) + 1);
    });

    nodeIdCounts.forEach((count, nodeId) => {
      if (count > 1) {
        errors.push(`Duplicate node ID found: ${nodeId}`);
      }
    });

    // Check for self-loops
    links.forEach((link) => {
      if (link.source_node_id === link.target_node_id) {
        errors.push(`Self-loop detected on node ${link.source_node_id}`);
      }
    });

    return {
      valid: errors.length === 0,
      errors,
    };
  },
};
