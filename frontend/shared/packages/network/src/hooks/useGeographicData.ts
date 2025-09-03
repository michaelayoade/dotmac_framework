/**
 * Geographic data management hook for network coverage analysis
 * Handles service areas, coverage gaps, and network node geographic data
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useApiClient } from '@dotmac/headless';
import { io, Socket } from 'socket.io-client';
import type {
  ServiceArea,
  CoverageGap,
  NetworkNode,
  UseGeographicDataOptions,
  UseGeographicDataResult,
} from '../types';

export function useGeographicData(options: UseGeographicDataOptions): UseGeographicDataResult {
  const { tenant_id, include_coverage_analysis = false } = options;

  const apiClient = useApiClient();

  // State management
  const [serviceAreas, setServiceAreas] = useState<ServiceArea[]>([]);
  const [coverageGaps, setCoverageGaps] = useState<CoverageGap[]>([]);
  const [networkNodes, setNetworkNodes] = useState<NetworkNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // WebSocket connection for real-time geographic updates
  const socketRef = useRef<Socket | null>(null);

  // Initialize WebSocket connection
  useEffect(() => {
    if (!tenant_id) return;

    const socket = io('/geographic-data', {
      auth: { tenant_id },
      transports: ['websocket'],
    });

    socket.on('connect', () => {
      console.log('Connected to geographic data updates');
      socket.emit('subscribe_geographic', { tenant_id });
    });

    socket.on('service_area_updated', (updatedArea: ServiceArea) => {
      setServiceAreas((prev) =>
        prev.map((area) => (area.id === updatedArea.id ? updatedArea : area))
      );
    });

    socket.on('coverage_gap_detected', (newGap: CoverageGap) => {
      setCoverageGaps((prev) => [...prev, newGap]);
    });

    socket.on('coverage_gap_resolved', (gapId: string) => {
      setCoverageGaps((prev) => prev.filter((gap) => gap.id !== gapId));
    });

    socket.on('network_node_moved', (updatedNode: NetworkNode) => {
      setNetworkNodes((prev) =>
        prev.map((node) => (node.node_id === updatedNode.node_id ? updatedNode : node))
      );
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from geographic data updates');
    });

    socket.on('error', (socketError: any) => {
      console.error('Geographic data socket error:', socketError);
      setError(`Geographic data connection error: ${socketError.message}`);
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [tenant_id]);

  // Fetch geographic data
  const fetchGeographicData = useCallback(async () => {
    if (!tenant_id) return;

    try {
      setError(null);

      // Fetch service areas
      const areasResponse = await apiClient.get(`/api/gis/service-areas?tenant_id=${tenant_id}`);
      setServiceAreas(areasResponse.data || []);

      // Fetch network nodes with geographic coordinates
      const nodesResponse = await apiClient.get(
        `/api/network/topology/nodes?tenant_id=${tenant_id}&include_coordinates=true`
      );
      setNetworkNodes(
        nodesResponse.data?.filter((node: NetworkNode) => node.latitude && node.longitude) || []
      );

      // Fetch coverage gaps if requested
      if (include_coverage_analysis) {
        const gapsResponse = await apiClient.get(
          `/api/gis/coverage-gaps?tenant_id=${tenant_id}&status=active`
        );
        setCoverageGaps(gapsResponse.data || []);
      }
    } catch (err: any) {
      console.error('Failed to fetch geographic data:', err);
      setError(err.message || 'Failed to fetch geographic data');
    } finally {
      setLoading(false);
    }
  }, [tenant_id, include_coverage_analysis, apiClient]);

  // Analyze coverage for all service areas
  const analyzeCoverage = useCallback(async () => {
    if (!tenant_id) {
      throw new Error('Tenant ID is required');
    }

    try {
      setLoading(true);

      const response = await apiClient.post('/api/gis/analyze-coverage', {
        tenant_id,
      });

      // Refresh data after analysis
      await fetchGeographicData();

      return response.data;
    } catch (err: any) {
      console.error('Coverage analysis failed:', err);
      setError(err.message || 'Failed to analyze coverage');
      throw new Error(err.message || 'Failed to analyze coverage');
    }
  }, [tenant_id, apiClient, fetchGeographicData]);

  // Manual refresh function
  const refresh = useCallback(async () => {
    setLoading(true);
    await fetchGeographicData();
  }, [fetchGeographicData]);

  // Initial data load
  useEffect(() => {
    fetchGeographicData();
  }, [fetchGeographicData]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  return {
    service_areas: serviceAreas,
    coverage_gaps: coverageGaps,
    network_nodes: networkNodes,
    loading,
    error,
    analyze_coverage: analyzeCoverage,
    refresh,
  };
}

// Hook for managing individual service area
export function useServiceArea(serviceAreaId: string) {
  const [serviceArea, setServiceArea] = useState<ServiceArea | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  useEffect(() => {
    if (!serviceAreaId) return;

    const fetchServiceArea = async () => {
      try {
        setError(null);
        const response = await apiClient.get(`/api/gis/service-areas/${serviceAreaId}`);
        setServiceArea(response.data);
      } catch (err: any) {
        console.error('Failed to fetch service area:', err);
        setError(err.message || 'Failed to fetch service area');
      } finally {
        setLoading(false);
      }
    };

    fetchServiceArea();
  }, [serviceAreaId, apiClient]);

  const updateServiceArea = useCallback(
    async (updates: Partial<ServiceArea>) => {
      if (!serviceAreaId) {
        throw new Error('Service area ID is required');
      }

      try {
        const response = await apiClient.patch(`/api/gis/service-areas/${serviceAreaId}`, updates);
        setServiceArea(response.data);
        return response.data;
      } catch (err: any) {
        console.error('Failed to update service area:', err);
        throw new Error(err.message || 'Failed to update service area');
      }
    },
    [serviceAreaId, apiClient]
  );

  return {
    service_area: serviceArea,
    loading,
    error,
    update: updateServiceArea,
  };
}

// Hook for coverage gap management
export function useCoverageGaps(tenantId: string) {
  const [coverageGaps, setCoverageGaps] = useState<CoverageGap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  useEffect(() => {
    if (!tenantId) return;

    const fetchCoverageGaps = async () => {
      try {
        setError(null);
        const response = await apiClient.get(`/api/gis/coverage-gaps?tenant_id=${tenantId}`);
        setCoverageGaps(response.data || []);
      } catch (err: any) {
        console.error('Failed to fetch coverage gaps:', err);
        setError(err.message || 'Failed to fetch coverage gaps');
      } finally {
        setLoading(false);
      }
    };

    fetchCoverageGaps();
  }, [tenantId, apiClient]);

  const resolveGap = useCallback(
    async (gapId: string, resolution: string) => {
      try {
        await apiClient.patch(`/api/gis/coverage-gaps/${gapId}`, {
          status: 'resolved',
          resolution_notes: resolution,
        });

        setCoverageGaps((prev) => prev.filter((gap) => gap.id !== gapId));
      } catch (err: any) {
        console.error('Failed to resolve coverage gap:', err);
        throw new Error(err.message || 'Failed to resolve coverage gap');
      }
    },
    [apiClient]
  );

  const updateGapPriority = useCallback(
    async (gapId: string, priorityScore: number) => {
      try {
        const response = await apiClient.patch(`/api/gis/coverage-gaps/${gapId}`, {
          priority_score: priorityScore,
        });

        setCoverageGaps((prev) =>
          prev.map((gap) => (gap.id === gapId ? { ...gap, priority_score: priorityScore } : gap))
        );

        return response.data;
      } catch (err: any) {
        console.error('Failed to update gap priority:', err);
        throw new Error(err.message || 'Failed to update gap priority');
      }
    },
    [apiClient]
  );

  return {
    coverage_gaps: coverageGaps,
    loading,
    error,
    resolve_gap: resolveGap,
    update_priority: updateGapPriority,
  };
}

// Hook for route optimization
export function useRouteOptimization() {
  const [optimizedRoute, setOptimizedRoute] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  const optimizeRoute = useCallback(
    async (routeParams: {
      start_coordinates: { latitude: number; longitude: number };
      waypoints: { latitude: number; longitude: number; name?: string }[];
      end_coordinates?: { latitude: number; longitude: number };
      optimization_type?: 'shortest' | 'fastest' | 'most_efficient';
      vehicle_type?: string;
    }) => {
      setLoading(true);
      setError(null);

      try {
        const response = await apiClient.post('/api/gis/optimize-route', routeParams);
        setOptimizedRoute(response.data);
        return response.data;
      } catch (err: any) {
        console.error('Route optimization failed:', err);
        setError(err.message || 'Failed to optimize route');
        throw new Error(err.message || 'Failed to optimize route');
      } finally {
        setLoading(false);
      }
    },
    [apiClient]
  );

  const clearRoute = useCallback(() => {
    setOptimizedRoute(null);
    setError(null);
  }, []);

  return {
    optimized_route: optimizedRoute,
    loading,
    error,
    optimize: optimizeRoute,
    clear: clearRoute,
  };
}
