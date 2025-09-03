/**
 * Network topology management hook
 * Provides comprehensive network topology data and operations
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useApiClient } from '@dotmac/headless';
import { io, Socket } from 'socket.io-client';
import type {
  NetworkNode,
  NetworkLink,
  TopologyMetrics,
  CriticalNode,
  PathAnalysis,
  UseNetworkTopologyOptions,
  UseNetworkTopologyResult,
  NetworkAlert,
  PerformanceMetric,
} from '../types';

export function useNetworkTopology(options: UseNetworkTopologyOptions): UseNetworkTopologyResult {
  const {
    tenant_id,
    auto_refresh = false,
    refresh_interval = 30000,
    include_performance_metrics = false,
  } = options;

  const apiClient = useApiClient();

  // State management
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [links, setLinks] = useState<NetworkLink[]>([]);
  const [topologyMetrics, setTopologyMetrics] = useState<TopologyMetrics | undefined>();
  const [criticalNodes, setCriticalNodes] = useState<CriticalNode[] | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // WebSocket connection for real-time updates
  const socketRef = useRef<Socket | null>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize WebSocket connection for real-time topology updates
  useEffect(() => {
    if (!tenant_id) return;

    const socket = io('/network-topology', {
      auth: { tenant_id },
      transports: ['websocket'],
    });

    socket.on('connect', () => {
      console.log('Connected to network topology updates');
      socket.emit('subscribe', { tenant_id, include_metrics: include_performance_metrics });
    });

    socket.on('node_updated', (updatedNode: NetworkNode) => {
      setNodes((prev) =>
        prev.map((node) => (node.node_id === updatedNode.node_id ? updatedNode : node))
      );
    });

    socket.on('link_updated', (updatedLink: NetworkLink) => {
      setLinks((prev) =>
        prev.map((link) => (link.link_id === updatedLink.link_id ? updatedLink : link))
      );
    });

    socket.on('node_added', (newNode: NetworkNode) => {
      setNodes((prev) => [...prev, newNode]);
    });

    socket.on('node_removed', (nodeId: string) => {
      setNodes((prev) => prev.filter((node) => node.node_id !== nodeId));
      setLinks((prev) =>
        prev.filter((link) => link.source_node_id !== nodeId && link.target_node_id !== nodeId)
      );
    });

    socket.on('link_added', (newLink: NetworkLink) => {
      setLinks((prev) => [...prev, newLink]);
    });

    socket.on('link_removed', (linkId: string) => {
      setLinks((prev) => prev.filter((link) => link.link_id !== linkId));
    });

    socket.on('topology_metrics_updated', (metrics: TopologyMetrics) => {
      setTopologyMetrics(metrics);
    });

    socket.on('critical_nodes_updated', (criticalNodesData: CriticalNode[]) => {
      setCriticalNodes(criticalNodesData);
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from network topology updates');
    });

    socket.on('error', (socketError: any) => {
      console.error('Socket error:', socketError);
      setError(`Real-time connection error: ${socketError.message}`);
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [tenant_id, include_performance_metrics]);

  // Fetch topology data
  const fetchTopology = useCallback(async () => {
    if (!tenant_id) return;

    try {
      setError(null);

      const [nodesResponse, linksResponse] = await Promise.all([
        apiClient.get(`/api/network/topology/nodes?tenant_id=${tenant_id}`),
        apiClient.get(`/api/network/topology/links?tenant_id=${tenant_id}`),
      ]);

      setNodes(nodesResponse.data || []);
      setLinks(linksResponse.data || []);

      // Fetch additional analysis data
      if (include_performance_metrics) {
        const [metricsResponse, criticalResponse] = await Promise.all([
          apiClient.get(`/api/network/topology/metrics?tenant_id=${tenant_id}`),
          apiClient.get(`/api/network/topology/critical-nodes?tenant_id=${tenant_id}`),
        ]);

        setTopologyMetrics(metricsResponse.data);
        setCriticalNodes(criticalResponse.data);
      }
    } catch (err: any) {
      console.error('Failed to fetch topology:', err);
      setError(err.message || 'Failed to fetch network topology');
    } finally {
      setLoading(false);
    }
  }, [tenant_id, include_performance_metrics, apiClient]);

  // Auto-refresh setup
  useEffect(() => {
    if (auto_refresh && refresh_interval > 0) {
      refreshIntervalRef.current = setInterval(fetchTopology, refresh_interval);
      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
        }
      };
    }
  }, [auto_refresh, refresh_interval, fetchTopology]);

  // Initial data load
  useEffect(() => {
    fetchTopology();
  }, [fetchTopology]);

  // Analyze path between two nodes
  const analyzePath = useCallback(
    async (source: string, target: string): Promise<PathAnalysis> => {
      if (!tenant_id) {
        throw new Error('Tenant ID is required');
      }

      try {
        const response = await apiClient.post('/api/network/topology/analyze-path', {
          tenant_id,
          source_device: source,
          target_device: target,
        });

        return response.data;
      } catch (err: any) {
        console.error('Path analysis failed:', err);
        throw new Error(err.message || 'Failed to analyze network path');
      }
    },
    [tenant_id, apiClient]
  );

  // Get detailed connectivity information for a node
  const getNodeConnectivity = useCallback(
    async (nodeId: string) => {
      if (!tenant_id) {
        throw new Error('Tenant ID is required');
      }

      try {
        const response = await apiClient.get(
          `/api/network/topology/nodes/${nodeId}/connectivity?tenant_id=${tenant_id}`
        );
        return response.data;
      } catch (err: any) {
        console.error('Failed to get node connectivity:', err);
        throw new Error(err.message || 'Failed to get node connectivity information');
      }
    },
    [tenant_id, apiClient]
  );

  // Manual refresh function
  const refresh = useCallback(async () => {
    setLoading(true);
    await fetchTopology();
  }, [fetchTopology]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, []);

  return {
    nodes,
    links,
    topology_metrics: topologyMetrics,
    critical_nodes: criticalNodes,
    loading,
    error,
    refresh,
    analyze_path: analyzePath,
    get_node_connectivity: getNodeConnectivity,
  };
}

// Additional hooks for specific network topology features

export function useNetworkPath(sourceNode?: string, targetNode?: string) {
  const [pathAnalysis, setPathAnalysis] = useState<PathAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  const analyzePath = useCallback(
    async (source: string, target: string) => {
      if (!source || !target) return;

      setLoading(true);
      setError(null);

      try {
        const response = await apiClient.post('/api/network/topology/analyze-path', {
          source_device: source,
          target_device: target,
        });

        setPathAnalysis(response.data);
      } catch (err: any) {
        console.error('Path analysis failed:', err);
        setError(err.message || 'Failed to analyze path');
      } finally {
        setLoading(false);
      }
    },
    [apiClient]
  );

  useEffect(() => {
    if (sourceNode && targetNode) {
      analyzePath(sourceNode, targetNode);
    }
  }, [sourceNode, targetNode, analyzePath]);

  return {
    path_analysis: pathAnalysis,
    loading,
    error,
    analyze: analyzePath,
    clear: () => setPathAnalysis(null),
  };
}

export function useTopologyMetrics(tenantId: string, autoRefresh = false) {
  const [metrics, setMetrics] = useState<TopologyMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  const fetchMetrics = useCallback(async () => {
    if (!tenantId) return;

    try {
      setError(null);
      const response = await apiClient.get(`/api/network/topology/metrics?tenant_id=${tenantId}`);
      setMetrics(response.data);
    } catch (err: any) {
      console.error('Failed to fetch topology metrics:', err);
      setError(err.message || 'Failed to fetch metrics');
    } finally {
      setLoading(false);
    }
  }, [tenantId, apiClient]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchMetrics, 30000); // 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, fetchMetrics]);

  return {
    metrics,
    loading,
    error,
    refresh: fetchMetrics,
  };
}

export function useNetworkAlerts(tenantId: string) {
  const [alerts, setAlerts] = useState<NetworkAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    if (!tenantId) return;

    // Fetch initial alerts
    const fetchAlerts = async () => {
      try {
        const response = await apiClient.get(
          `/api/network/alerts?tenant_id=${tenantId}&status=active`
        );
        setAlerts(response.data || []);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch alerts');
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();

    // Set up real-time alert updates
    const socket = io('/network-alerts', {
      auth: { tenant_id: tenantId },
    });

    socket.on('alert_created', (alert: NetworkAlert) => {
      setAlerts((prev) => [alert, ...prev]);
    });

    socket.on('alert_updated', (updatedAlert: NetworkAlert) => {
      setAlerts((prev) =>
        prev.map((alert) => (alert.id === updatedAlert.id ? updatedAlert : alert))
      );
    });

    socket.on('alert_resolved', (alertId: string) => {
      setAlerts((prev) => prev.filter((alert) => alert.id !== alertId));
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, [tenantId, apiClient]);

  const acknowledgeAlert = useCallback(
    async (alertId: string) => {
      try {
        await apiClient.patch(`/api/network/alerts/${alertId}`, {
          status: 'acknowledged',
        });
      } catch (err: any) {
        console.error('Failed to acknowledge alert:', err);
        throw new Error(err.message || 'Failed to acknowledge alert');
      }
    },
    [apiClient]
  );

  const resolveAlert = useCallback(
    async (alertId: string) => {
      try {
        await apiClient.patch(`/api/network/alerts/${alertId}`, {
          status: 'resolved',
        });
      } catch (err: any) {
        console.error('Failed to resolve alert:', err);
        throw new Error(err.message || 'Failed to resolve alert');
      }
    },
    [apiClient]
  );

  return {
    alerts,
    loading,
    error,
    acknowledge_alert: acknowledgeAlert,
    resolve_alert: resolveAlert,
  };
}
