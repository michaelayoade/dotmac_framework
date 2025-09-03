'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  WifiOff,
  Zap,
  TrendingUp,
  TrendingDown,
  Gauge,
  Radio,
  Signal,
  Clock,
} from 'lucide-react';

interface NetworkMetrics {
  timestamp: number;
  nodeId: string;
  nodeName: string;
  metrics: {
    cpu: number;
    memory: number;
    bandwidth: number;
    latency: number;
    packetLoss: number;
    uptime: number;
    temperature: number;
    powerDraw: number;
  };
  status: 'online' | 'degraded' | 'critical' | 'offline';
  alerts: {
    id: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    message: string;
    timestamp: number;
  }[];
}

interface RealTimeAlert {
  id: string;
  nodeId: string;
  nodeName: string;
  type: 'threshold' | 'outage' | 'degradation' | 'maintenance';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: number;
  acknowledged: boolean;
  details?: {
    metricName?: string;
    threshold?: number;
    currentValue?: number;
    duration?: number;
  };
}

interface RealTimeMonitoringDashboardProps {
  autoConnect?: boolean;
  refreshInterval?: number;
  onAlert?: (alert: RealTimeAlert) => void;
  onMetricsUpdate?: (metrics: NetworkMetrics[]) => void;
}

export function RealTimeMonitoringDashboard({
  autoConnect = true,
  refreshInterval = 5000,
  onAlert,
  onMetricsUpdate,
}: RealTimeMonitoringDashboardProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [metrics, setMetrics] = useState<NetworkMetrics[]>([]);
  const [alerts, setAlerts] = useState<RealTimeAlert[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'disconnected' | 'error'
  >('disconnected');
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const metricsIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Mock WebSocket simulation for demonstration
  const simulateWebSocketConnection = useCallback(() => {
    setConnectionStatus('connecting');

    // Simulate connection delay
    setTimeout(() => {
      setIsConnected(true);
      setConnectionStatus('connected');
      setLastUpdate(new Date());

      // Start sending mock data
      const interval = setInterval(() => {
        const mockMetrics = generateMockMetrics();
        const mockAlert = generateMockAlert();

        setMetrics((prev) => {
          const updated = [...prev.slice(-9), ...mockMetrics]; // Keep last 10 entries per node
          onMetricsUpdate?.(updated);
          return updated;
        });

        if (mockAlert && Math.random() < 0.1) {
          // 10% chance of alert
          setAlerts((prev) => {
            const newAlerts = [mockAlert, ...prev.slice(0, 19)]; // Keep last 20 alerts
            onAlert?.(mockAlert);
            return newAlerts;
          });
        }

        setLastUpdate(new Date());
      }, refreshInterval);

      metricsIntervalRef.current = interval;
    }, 1000);
  }, [refreshInterval, onAlert, onMetricsUpdate]);

  const generateMockMetrics = (): NetworkMetrics[] => {
    const nodes = [
      { id: 'SEA-CORE-01', name: 'Seattle Core Router' },
      { id: 'BEL-DIST-02', name: 'Bellevue Distribution' },
      { id: 'RED-DIST-03', name: 'Redmond Distribution' },
      { id: 'KIR-DIST-04', name: 'Kirkland Distribution' },
    ];

    return nodes.map((node) => ({
      timestamp: Date.now(),
      nodeId: node.id,
      nodeName: node.name,
      metrics: {
        cpu: 30 + Math.random() * 40,
        memory: 40 + Math.random() * 35,
        bandwidth: 50 + Math.random() * 30,
        latency: 5 + Math.random() * 10,
        packetLoss: Math.random() * 0.5,
        uptime: 99 + Math.random() * 0.99,
        temperature: 35 + Math.random() * 15,
        powerDraw: 150 + Math.random() * 50,
      },
      status: Math.random() > 0.9 ? 'degraded' : 'online',
      alerts: [],
    }));
  };

  const generateMockAlert = (): RealTimeAlert | null => {
    const alertTypes = [
      { type: 'threshold', severity: 'medium', message: 'CPU utilization above 80%' },
      { type: 'degradation', severity: 'high', message: 'High latency detected' },
      { type: 'outage', severity: 'critical', message: 'Node unreachable' },
      { type: 'threshold', severity: 'low', message: 'Memory usage increasing' },
    ];

    const nodes = ['SEA-CORE-01', 'BEL-DIST-02', 'RED-DIST-03', 'KIR-DIST-04'];
    const nodeNames = [
      'Seattle Core Router',
      'Bellevue Distribution',
      'Redmond Distribution',
      'Kirkland Distribution',
    ];

    const randomAlert = alertTypes[Math.floor(Math.random() * alertTypes.length)];
    const randomNodeIndex = Math.floor(Math.random() * nodes.length);

    return {
      id: `ALERT-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      nodeId: nodes[randomNodeIndex],
      nodeName: nodeNames[randomNodeIndex],
      type: randomAlert.type as any,
      severity: randomAlert.severity as any,
      message: randomAlert.message,
      timestamp: Date.now(),
      acknowledged: false,
      details: {
        metricName: 'cpu',
        threshold: 80,
        currentValue: 85.2,
        duration: 300,
      },
    };
  };

  const connect = () => {
    if (connectionStatus === 'connecting' || connectionStatus === 'connected') return;
    simulateWebSocketConnection();
  };

  const disconnect = () => {
    setIsConnected(false);
    setConnectionStatus('disconnected');
    if (metricsIntervalRef.current) {
      clearInterval(metricsIntervalRef.current);
      metricsIntervalRef.current = null;
    }
  };

  const acknowledgeAlert = (alertId: string) => {
    setAlerts((prev) =>
      prev.map((alert) => (alert.id === alertId ? { ...alert, acknowledged: true } : alert))
    );
  };

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [autoConnect]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return 'text-green-600 bg-green-100';
      case 'connecting':
        return 'text-blue-600 bg-blue-100';
      case 'disconnected':
        return 'text-gray-600 bg-gray-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-100 border-red-200';
      case 'high':
        return 'text-orange-600 bg-orange-100 border-orange-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100 border-yellow-200';
      case 'low':
        return 'text-blue-600 bg-blue-100 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-100 border-gray-200';
    }
  };

  const latestMetrics = metrics.reduce(
    (acc, metric) => {
      acc[metric.nodeId] = metric;
      return acc;
    },
    {} as Record<string, NetworkMetrics>
  );

  const criticalAlerts = alerts.filter(
    (alert) => alert.severity === 'critical' && !alert.acknowledged
  );
  const unacknowledgedAlerts = alerts.filter((alert) => !alert.acknowledged);

  return (
    <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
      <div className='flex justify-between items-center mb-6'>
        <div>
          <h3 className='text-lg font-semibold text-gray-900'>Real-Time Network Monitoring</h3>
          <p className='text-sm text-gray-600'>Live network metrics and alerts via WebSocket</p>
        </div>

        <div className='flex gap-3 items-center'>
          <div className='flex items-center gap-2 text-sm'>
            <div
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-400'}`}
            ></div>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(connectionStatus)}`}
            >
              {connectionStatus}
            </span>
            {lastUpdate && (
              <span className='text-xs text-gray-500'>Last: {lastUpdate.toLocaleTimeString()}</span>
            )}
          </div>

          <div className='flex gap-2'>
            {!isConnected ? (
              <button
                onClick={connect}
                className='px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700'
              >
                Connect
              </button>
            ) : (
              <button
                onClick={disconnect}
                className='px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700'
              >
                Disconnect
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Alert Summary */}
      {unacknowledgedAlerts.length > 0 && (
        <div className='mb-6 p-4 bg-red-50 border border-red-200 rounded-lg'>
          <div className='flex items-center gap-2 mb-2'>
            <AlertTriangle className='h-5 w-5 text-red-600' />
            <span className='font-medium text-red-900'>
              {criticalAlerts.length} Critical • {unacknowledgedAlerts.length} Total Unacknowledged
              Alerts
            </span>
          </div>
          <div className='text-sm text-red-700'>
            Latest: {unacknowledgedAlerts[0]?.message} ({unacknowledgedAlerts[0]?.nodeName})
          </div>
        </div>
      )}

      <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
        {/* Real-Time Metrics */}
        <div className='lg:col-span-2 space-y-4'>
          <h4 className='font-medium text-gray-900'>Live Network Metrics</h4>

          {Object.values(latestMetrics).length > 0 ? (
            <div className='space-y-4'>
              {Object.values(latestMetrics).map((metric) => (
                <div key={metric.nodeId} className='border border-gray-200 rounded-lg p-4'>
                  <div className='flex items-center justify-between mb-3'>
                    <div className='flex items-center gap-2'>
                      <div
                        className={`w-3 h-3 rounded-full ${
                          metric.status === 'online'
                            ? 'bg-green-500'
                            : metric.status === 'degraded'
                              ? 'bg-yellow-500'
                              : metric.status === 'critical'
                                ? 'bg-red-500'
                                : 'bg-gray-500'
                        }`}
                      ></div>
                      <span className='font-medium text-gray-900'>{metric.nodeName}</span>
                    </div>
                    <span className='text-xs text-gray-500'>
                      {new Date(metric.timestamp).toLocaleTimeString()}
                    </span>
                  </div>

                  <div className='grid grid-cols-4 gap-4 text-sm'>
                    <div>
                      <div className='flex items-center gap-1 text-gray-600 mb-1'>
                        <Gauge className='h-3 w-3' />
                        <span>CPU</span>
                      </div>
                      <div
                        className={`font-medium ${metric.metrics.cpu > 80 ? 'text-red-600' : 'text-gray-900'}`}
                      >
                        {metric.metrics.cpu.toFixed(1)}%
                      </div>
                    </div>

                    <div>
                      <div className='flex items-center gap-1 text-gray-600 mb-1'>
                        <Activity className='h-3 w-3' />
                        <span>Memory</span>
                      </div>
                      <div
                        className={`font-medium ${metric.metrics.memory > 85 ? 'text-red-600' : 'text-gray-900'}`}
                      >
                        {metric.metrics.memory.toFixed(1)}%
                      </div>
                    </div>

                    <div>
                      <div className='flex items-center gap-1 text-gray-600 mb-1'>
                        <Signal className='h-3 w-3' />
                        <span>Bandwidth</span>
                      </div>
                      <div
                        className={`font-medium ${metric.metrics.bandwidth > 90 ? 'text-red-600' : 'text-gray-900'}`}
                      >
                        {metric.metrics.bandwidth.toFixed(1)}%
                      </div>
                    </div>

                    <div>
                      <div className='flex items-center gap-1 text-gray-600 mb-1'>
                        <Clock className='h-3 w-3' />
                        <span>Latency</span>
                      </div>
                      <div
                        className={`font-medium ${metric.metrics.latency > 20 ? 'text-red-600' : 'text-gray-900'}`}
                      >
                        {metric.metrics.latency.toFixed(1)}ms
                      </div>
                    </div>
                  </div>

                  {/* Additional metrics row */}
                  <div className='grid grid-cols-4 gap-4 text-sm mt-3 pt-3 border-t border-gray-100'>
                    <div>
                      <span className='text-gray-600'>Uptime: </span>
                      <span className='font-medium'>{metric.metrics.uptime.toFixed(2)}%</span>
                    </div>
                    <div>
                      <span className='text-gray-600'>Temp: </span>
                      <span className='font-medium'>{metric.metrics.temperature.toFixed(1)}°C</span>
                    </div>
                    <div>
                      <span className='text-gray-600'>Power: </span>
                      <span className='font-medium'>{metric.metrics.powerDraw.toFixed(0)}W</span>
                    </div>
                    <div>
                      <span className='text-gray-600'>Loss: </span>
                      <span className='font-medium'>{metric.metrics.packetLoss.toFixed(3)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className='text-center py-8 text-gray-500'>
              <Radio className='h-8 w-8 mx-auto mb-2 text-gray-400' />
              <p>No real-time data available</p>
              <p className='text-sm'>Connect to start receiving live metrics</p>
            </div>
          )}
        </div>

        {/* Alerts Panel */}
        <div>
          <h4 className='font-medium text-gray-900 mb-4'>Recent Alerts</h4>

          <div className='space-y-3 max-h-96 overflow-y-auto'>
            {alerts.length > 0 ? (
              alerts.slice(0, 10).map((alert) => (
                <div
                  key={alert.id}
                  className={`border rounded-lg p-3 ${getSeverityColor(alert.severity)} ${
                    alert.acknowledged ? 'opacity-60' : ''
                  }`}
                >
                  <div className='flex items-start justify-between mb-2'>
                    <div className='flex items-center gap-2'>
                      {alert.severity === 'critical' ? (
                        <AlertTriangle className='h-4 w-4 text-red-600' />
                      ) : alert.severity === 'high' ? (
                        <TrendingUp className='h-4 w-4 text-orange-600' />
                      ) : (
                        <Activity className='h-4 w-4 text-yellow-600' />
                      )}
                      <span className='text-xs font-medium uppercase'>{alert.severity}</span>
                    </div>
                    <span className='text-xs text-gray-500'>
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </span>
                  </div>

                  <p className='text-sm font-medium text-gray-900 mb-1'>{alert.message}</p>
                  <p className='text-xs text-gray-600 mb-2'>{alert.nodeName}</p>

                  {alert.details && (
                    <div className='text-xs text-gray-600 mb-2'>
                      {alert.details.metricName}: {alert.details.currentValue}
                      {alert.details.threshold && ` (threshold: ${alert.details.threshold})`}
                    </div>
                  )}

                  {!alert.acknowledged && (
                    <button
                      onClick={() => acknowledgeAlert(alert.id)}
                      className='text-xs px-2 py-1 bg-white bg-opacity-80 border border-gray-300 rounded hover:bg-opacity-100'
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              ))
            ) : (
              <div className='text-center py-8 text-gray-500'>
                <CheckCircle className='h-8 w-8 mx-auto mb-2 text-gray-400' />
                <p className='text-sm'>No recent alerts</p>
                <p className='text-xs'>All systems operating normally</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Connection Info */}
      <div className='mt-6 pt-4 border-t border-gray-200 text-xs text-gray-500'>
        <div className='flex justify-between items-center'>
          <div>
            WebSocket Status: {connectionStatus} • Metrics: {Object.keys(latestMetrics).length}{' '}
            nodes • Alerts: {alerts.length} total ({unacknowledgedAlerts.length} unack)
          </div>
          <div>Refresh Rate: {refreshInterval / 1000}s</div>
        </div>
      </div>
    </div>
  );
}
