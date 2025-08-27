/**
 * Monitoring Dashboard - Real-time observability for admin operations
 * Displays system health, performance metrics, and operational insights
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  ActivityIcon,
  AlertTriangleIcon,
  BarChart3Icon,
  CpuIcon,
  DatabaseIcon,
  GaugeIcon,
  NetworkIcon,
  TrendingUpIcon,
  UsersIcon,
  WifiIcon,
} from 'lucide-react';
import { usePerformanceMonitor } from '../../lib/monitoring';
import { ConnectionStatus } from '../realtime/ConnectionStatus';

interface SystemMetric {
  name: string;
  value: number;
  unit: string;
  status: 'good' | 'warning' | 'critical';
  trend?: 'up' | 'down' | 'stable';
}

interface AlertInfo {
  id: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  timestamp: Date;
  resolved: boolean;
}

export function MonitoringDashboard() {
  const { trackInteraction, trackBusinessMetric } = usePerformanceMonitor();
  const [systemMetrics, setSystemMetrics] = useState<SystemMetric[]>([]);
  const [alerts, setAlerts] = useState<AlertInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    trackInteraction('view_monitoring_dashboard', 'dashboard');
    loadMonitoringData();
    
    // Refresh data every 30 seconds
    const interval = setInterval(loadMonitoringData, 30000);
    return () => clearInterval(interval);
  }, [trackInteraction]);

  const loadMonitoringData = async () => {
    try {
      // Simulated data - in real implementation, this would come from your monitoring API
      const metrics: SystemMetric[] = [
        {
          name: 'Response Time',
          value: 245,
          unit: 'ms',
          status: 'good',
          trend: 'stable',
        },
        {
          name: 'Error Rate',
          value: 0.2,
          unit: '%',
          status: 'good',
          trend: 'down',
        },
        {
          name: 'Throughput',
          value: 1247,
          unit: 'req/min',
          status: 'good',
          trend: 'up',
        },
        {
          name: 'Memory Usage',
          value: 68,
          unit: '%',
          status: 'warning',
          trend: 'up',
        },
        {
          name: 'Database Connections',
          value: 15,
          unit: 'active',
          status: 'good',
          trend: 'stable',
        },
        {
          name: 'WebSocket Connections',
          value: 234,
          unit: 'active',
          status: 'good',
          trend: 'up',
        },
      ];

      const mockAlerts: AlertInfo[] = [
        {
          id: '1',
          severity: 'warning',
          message: 'High memory usage detected on billing service',
          timestamp: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
          resolved: false,
        },
        {
          id: '2',
          severity: 'info',
          message: 'Scheduled maintenance completed successfully',
          timestamp: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
          resolved: true,
        },
      ];

      setSystemMetrics(metrics);
      setAlerts(mockAlerts);
      setIsLoading(false);

      trackBusinessMetric('monitoring_dashboard_load', 1, { success: 'true' });
    } catch (error) {
      console.error('Failed to load monitoring data:', error);
      trackBusinessMetric('monitoring_dashboard_load', 1, { success: 'false' });
      setIsLoading(false);
    }
  };

  const getMetricIcon = (metricName: string) => {
    const iconMap: Record<string, React.ComponentType<any>> = {
      'Response Time': GaugeIcon,
      'Error Rate': AlertTriangleIcon,
      'Throughput': BarChart3Icon,
      'Memory Usage': CpuIcon,
      'Database Connections': DatabaseIcon,
      'WebSocket Connections': NetworkIcon,
    };
    return iconMap[metricName] || ActivityIcon;
  };

  const getStatusColor = (status: SystemMetric['status']) => {
    switch (status) {
      case 'good':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getTrendIcon = (trend?: SystemMetric['trend']) => {
    switch (trend) {
      case 'up':
        return <TrendingUpIcon className="w-3 h-3 text-green-600" />;
      case 'down':
        return <TrendingUpIcon className="w-3 h-3 text-red-600 rotate-180" />;
      default:
        return <div className="w-2 h-2 bg-gray-400 rounded-full" />;
    }
  };

  const getAlertSeverityColor = (severity: AlertInfo['severity']) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'info':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading monitoring data...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Monitoring</h1>
          <p className="text-gray-600">Real-time system health and performance metrics</p>
        </div>
        <ConnectionStatus showDetails={false} />
      </div>

      {/* System Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {systemMetrics.map((metric) => {
          const MetricIcon = getMetricIcon(metric.name);
          return (
            <div
              key={metric.name}
              className={`p-4 rounded-lg border-2 ${getStatusColor(metric.status)}`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <MetricIcon className="w-5 h-5" />
                  <h3 className="font-medium">{metric.name}</h3>
                </div>
                {getTrendIcon(metric.trend)}
              </div>
              <div className="flex items-baseline space-x-1">
                <span className="text-2xl font-bold">{metric.value}</span>
                <span className="text-sm opacity-75">{metric.unit}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Alerts Section */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <AlertTriangleIcon className="w-5 h-5 text-yellow-600" />
            <h2 className="text-lg font-semibold text-gray-900">Recent Alerts</h2>
            <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
              {alerts.filter(a => !a.resolved).length} active
            </span>
          </div>
        </div>
        <div className="divide-y divide-gray-200">
          {alerts.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              <AlertTriangleIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No recent alerts</p>
            </div>
          ) : (
            alerts.map((alert) => (
              <div key={alert.id} className="p-4">
                <div className="flex items-start space-x-3">
                  <div
                    className={`px-2 py-1 text-xs font-medium rounded-full ${getAlertSeverityColor(alert.severity)}`}
                  >
                    {alert.severity.toUpperCase()}
                  </div>
                  <div className="flex-1">
                    <p className={`text-sm ${alert.resolved ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                      {alert.message}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {alert.timestamp.toLocaleString()}
                      {alert.resolved && ' • Resolved'}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Performance Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Real-time Connection Status */}
        <ConnectionStatus showDetails={true} className="h-fit" />

        {/* Quick Actions */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button
              onClick={() => {
                trackInteraction('trigger_health_check', 'monitoring_dashboard');
                // Implement health check trigger
              }}
              className="w-full flex items-center space-x-2 px-4 py-2 text-left text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
            >
              <ActivityIcon className="w-4 h-4" />
              <span>Run Health Check</span>
            </button>
            
            <button
              onClick={() => {
                trackInteraction('view_performance_metrics', 'monitoring_dashboard');
                // Navigate to detailed performance view
              }}
              className="w-full flex items-center space-x-2 px-4 py-2 text-left text-sm font-medium text-green-600 bg-green-50 rounded-lg hover:bg-green-100"
            >
              <BarChart3Icon className="w-4 h-4" />
              <span>View Detailed Metrics</span>
            </button>
            
            <button
              onClick={() => {
                trackInteraction('refresh_monitoring_data', 'monitoring_dashboard');
                setIsLoading(true);
                loadMonitoringData();
              }}
              className="w-full flex items-center space-x-2 px-4 py-2 text-left text-sm font-medium text-gray-600 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <DatabaseIcon className="w-4 h-4" />
              <span>Refresh Data</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}