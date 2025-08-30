/**
 * Network monitoring and alerting hook
 * Real-time performance monitoring and alert management
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useApiClient } from '@dotmac/headless';
import { io, Socket } from 'socket.io-client';
import type {
  NetworkAlert,
  PerformanceMetric,
  UseNetworkMonitoringOptions,
  UseNetworkMonitoringResult
} from '../types';

export function useNetworkMonitoring(options: UseNetworkMonitoringOptions): UseNetworkMonitoringResult {
  const {
    tenant_id,
    real_time = true,
    alert_thresholds = {}
  } = options;

  const apiClient = useApiClient();

  // State management
  const [performanceData, setPerformanceData] = useState<PerformanceMetric[]>([]);
  const [alerts, setAlerts] = useState<NetworkAlert[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // WebSocket connection for real-time monitoring
  const socketRef = useRef<Socket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize WebSocket connection for real-time monitoring
  const initializeSocket = useCallback(() => {
    if (!tenant_id || !real_time) return;

    setConnectionStatus('connecting');

    const socket = io('/network-monitoring', {
      auth: { tenant_id },
      transports: ['websocket'],
      timeout: 5000,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

    socket.on('connect', () => {
      console.log('Connected to network monitoring');
      setConnectionStatus('connected');
      setError(null);

      // Subscribe to monitoring data
      socket.emit('subscribe_monitoring', {
        tenant_id,
        alert_thresholds
      });
    });

    socket.on('performance_data', (metrics: PerformanceMetric[]) => {
      setPerformanceData(prev => {
        // Keep only last 1000 metrics to prevent memory issues
        const combined = [...prev, ...metrics];
        return combined.slice(-1000);
      });
    });

    socket.on('alert_created', (alert: NetworkAlert) => {
      setAlerts(prev => [alert, ...prev]);

      // Optional: Show browser notification for critical alerts
      if (alert.severity === 'critical' && 'Notification' in window && Notification.permission === 'granted') {
        new Notification(`Critical Network Alert: ${alert.message}`, {
          icon: '/icons/alert-critical.png',
          tag: `network-alert-${alert.id}`
        });
      }
    });

    socket.on('alert_updated', (updatedAlert: NetworkAlert) => {
      setAlerts(prev => prev.map(alert =>
        alert.id === updatedAlert.id ? updatedAlert : alert
      ));
    });

    socket.on('alert_resolved', (alertId: string) => {
      setAlerts(prev => prev.filter(alert => alert.id !== alertId));
    });

    socket.on('node_status_changed', (data: { node_id: string; status: string; timestamp: string }) => {
      // Update performance data with status change
      const statusMetric: PerformanceMetric = {
        timestamp: data.timestamp,
        metric_name: 'node_status',
        entity_id: data.node_id,
        entity_type: 'node',
        value: data.status === 'active' ? 1 : 0,
        unit: 'status'
      };

      setPerformanceData(prev => [...prev.slice(-999), statusMetric]);
    });

    socket.on('link_utilization_updated', (data: { link_id: string; utilization: number; timestamp: string }) => {
      const utilizationMetric: PerformanceMetric = {
        timestamp: data.timestamp,
        metric_name: 'link_utilization',
        entity_id: data.link_id,
        entity_type: 'link',
        value: data.utilization,
        unit: 'percentage'
      };

      setPerformanceData(prev => [...prev.slice(-999), utilizationMetric]);
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from network monitoring');
      setConnectionStatus('disconnected');
    });

    socket.on('connect_error', (err: any) => {
      console.error('Network monitoring connection error:', err);
      setConnectionStatus('disconnected');
      setError(`Connection error: ${err.message}`);

      // Attempt to reconnect after a delay
      if (!reconnectTimeoutRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect to network monitoring...');
          initializeSocket();
          reconnectTimeoutRef.current = null;
        }, 5000);
      }
    });

    socket.on('error', (socketError: any) => {
      console.error('Network monitoring socket error:', socketError);
      setError(`Monitoring error: ${socketError.message}`);
    });

    socketRef.current = socket;
  }, [tenant_id, real_time, alert_thresholds]);

  // Fetch initial monitoring data
  const fetchMonitoringData = useCallback(async () => {
    if (!tenant_id) return;

    try {
      setError(null);

      // Fetch current alerts
      const alertsResponse = await apiClient.get(
        `/api/network/alerts?tenant_id=${tenant_id}&status=active&limit=100`
      );
      setAlerts(alertsResponse.data || []);

      // Fetch recent performance data
      const performanceResponse = await apiClient.get(
        `/api/network/performance?tenant_id=${tenant_id}&limit=500`
      );
      setPerformanceData(performanceResponse.data || []);

    } catch (err: any) {
      console.error('Failed to fetch monitoring data:', err);
      setError(err.message || 'Failed to fetch monitoring data');
    } finally {
      setLoading(false);
    }
  }, [tenant_id, apiClient]);

  // Acknowledge an alert
  const acknowledgeAlert = useCallback(async (alertId: string) => {
    try {
      await apiClient.patch(`/api/network/alerts/${alertId}`, {
        status: 'acknowledged',
        acknowledged_at: new Date().toISOString()
      });

      setAlerts(prev => prev.map(alert =>
        alert.id === alertId
          ? { ...alert, status: 'acknowledged', acknowledged_at: new Date().toISOString() }
          : alert
      ));
    } catch (err: any) {
      console.error('Failed to acknowledge alert:', err);
      throw new Error(err.message || 'Failed to acknowledge alert');
    }
  }, [apiClient]);

  // Resolve an alert
  const resolveAlert = useCallback(async (alertId: string) => {
    try {
      await apiClient.patch(`/api/network/alerts/${alertId}`, {
        status: 'resolved',
        resolved_at: new Date().toISOString()
      });

      setAlerts(prev => prev.filter(alert => alert.id !== alertId));
    } catch (err: any) {
      console.error('Failed to resolve alert:', err);
      throw new Error(err.message || 'Failed to resolve alert');
    }
  }, [apiClient]);

  // Subscribe to real-time alerts
  const subscribeToAlerts = useCallback(() => {
    if (real_time && !socketRef.current) {
      initializeSocket();
    }
  }, [real_time, initializeSocket]);

  // Unsubscribe from real-time alerts
  const unsubscribeFromAlerts = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.emit('unsubscribe_monitoring', { tenant_id });
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, [tenant_id]);

  // Initialize monitoring on mount
  useEffect(() => {
    fetchMonitoringData();

    if (real_time) {
      initializeSocket();
    }

    // Request notification permission for critical alerts
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, [fetchMonitoringData, initializeSocket, real_time]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  // Reconnect when options change
  useEffect(() => {
    if (real_time && connectionStatus === 'disconnected' && !socketRef.current) {
      initializeSocket();
    }
  }, [real_time, connectionStatus, initializeSocket]);

  return {
    performance_data: performanceData,
    alerts,
    connection_status: connectionStatus,
    loading,
    error,
    acknowledge_alert: acknowledgeAlert,
    resolve_alert: resolveAlert,
    subscribe_to_alerts: subscribeToAlerts,
    unsubscribe_from_alerts: unsubscribeFromAlerts
  };
}

// Additional monitoring utilities

export function usePerformanceMetrics(entityId: string, entityType: 'node' | 'link', metricName?: string) {
  const [metrics, setMetrics] = useState<PerformanceMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  useEffect(() => {
    if (!entityId) return;

    const fetchMetrics = async () => {
      try {
        setError(null);

        let url = `/api/network/performance/entity/${entityId}?entity_type=${entityType}`;
        if (metricName) {
          url += `&metric_name=${metricName}`;
        }

        const response = await apiClient.get(url);
        setMetrics(response.data || []);
      } catch (err: any) {
        console.error('Failed to fetch performance metrics:', err);
        setError(err.message || 'Failed to fetch performance metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [entityId, entityType, metricName, apiClient]);

  return {
    metrics,
    loading,
    error
  };
}

export function useAlertFilters() {
  const [filters, setFilters] = useState({
    severity: [],
    type: [],
    status: ['active'],
    time_range: '24h'
  });

  const updateFilter = useCallback((key: string, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({
      severity: [],
      type: [],
      status: ['active'],
      time_range: '24h'
    });
  }, []);

  return {
    filters,
    updateFilter,
    clearFilters
  };
}
