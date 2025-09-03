/**
 * Network calculation utilities
 * Helper functions for network performance and capacity calculations
 */

import type { NetworkNode, NetworkLink, PerformanceMetric } from '../types';

export const networkCalculations = {
  /**
   * Calculate bandwidth utilization percentage
   */
  calculateUtilization: (currentBandwidth: number, maxBandwidth: number): number => {
    if (maxBandwidth <= 0) return 0;
    return Math.min((currentBandwidth / maxBandwidth) * 100, 100);
  },

  /**
   * Calculate network latency from hop count and distance
   */
  estimateLatency: (hopCount: number, totalDistanceKm?: number): number => {
    const baseLatency = hopCount * 0.5; // 0.5ms per hop
    const distanceLatency = totalDistanceKm ? totalDistanceKm * 0.005 : 0; // 5μs per km
    return baseLatency + distanceLatency;
  },

  /**
   * Calculate capacity planning metrics
   */
  calculateCapacityMetrics: (currentUtilization: number, growthRate: number = 0.2) => {
    const threshold = 80; // 80% utilization threshold
    const monthsToThreshold =
      currentUtilization >= threshold
        ? 0
        : Math.log(threshold / currentUtilization) / Math.log(1 + growthRate / 12);

    return {
      current_utilization: currentUtilization,
      threshold,
      months_to_threshold: Math.max(0, monthsToThreshold),
      requires_upgrade: currentUtilization >= threshold,
    };
  },

  /**
   * Calculate network reliability score
   */
  calculateReliabilityScore: (nodes: NetworkNode[], links: NetworkLink[]): number => {
    const totalNodes = nodes.length;
    const activeNodes = nodes.filter((node) => node.status === 'active').length;
    const totalLinks = links.length;
    const activeLinks = links.filter((link) => link.status === 'active').length;

    if (totalNodes === 0 || totalLinks === 0) return 0;

    const nodeReliability = activeNodes / totalNodes;
    const linkReliability = activeLinks / totalLinks;

    return (nodeReliability * 0.6 + linkReliability * 0.4) * 100;
  },

  /**
   * Calculate redundancy factor
   */
  calculateRedundancy: (nodes: NetworkNode[]): { [nodeId: string]: number } => {
    const redundancyMap: { [nodeId: string]: number } = {};

    nodes.forEach((node) => {
      const connectionCount = node.connected_links.length;
      // Redundancy factor: 0 = no redundancy, 1 = fully redundant
      redundancyMap[node.node_id] = Math.min(connectionCount / 2, 1);
    });

    return redundancyMap;
  },

  /**
   * Calculate performance trend
   */
  calculateTrend: (metrics: PerformanceMetric[]): 'improving' | 'stable' | 'degrading' => {
    if (metrics.length < 2) return 'stable';

    const recent = metrics.slice(-5); // Last 5 metrics
    const older = metrics.slice(-10, -5); // Previous 5 metrics

    const recentAvg = recent.reduce((sum, m) => sum + m.value, 0) / recent.length;
    const olderAvg =
      older.length > 0 ? older.reduce((sum, m) => sum + m.value, 0) / older.length : recentAvg;

    const change = ((recentAvg - olderAvg) / olderAvg) * 100;

    if (Math.abs(change) < 5) return 'stable';
    return change > 0 ? 'degrading' : 'improving';
  },
};
