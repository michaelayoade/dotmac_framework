/**
 * System Monitoring Dashboard Component
 * Integrates with existing monitoring infrastructure
 * Leverages ISP framework monitoring capabilities for management portal
 */

import React, { useState, useEffect } from 'react';
import {
  CpuChipIcon,
  CircleStackIcon,
  CloudIcon,
  ServerIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  ChartBarIcon,
  BoltIcon,
  WifiIcon,
  CogIcon,
  ArrowPathIcon,
  SignalIcon,
  DocumentChartBarIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/http';

interface SystemMetric {
  name: string;
  value: number;
  unit: string;
  status: 'healthy' | 'warning' | 'critical';
  trend: 'up' | 'down' | 'stable';
  timestamp: string;
}

interface ServiceStatus {
  service_name: string;
  status: 'healthy' | 'degraded' | 'down';
  uptime: number;
  response_time: number;
  error_rate: number;
  last_check: string;
  dependencies: string[];
}

interface AlertItem {
  id: string;
  type: 'system' | 'service' | 'security' | 'performance';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  timestamp: string;
  acknowledged: boolean;
}

interface SystemMonitoringDashboardProps {
  className?: string;
}

export function SystemMonitoringDashboard({ className = '' }: SystemMonitoringDashboardProps) {
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch system metrics
  const { data: systemMetrics = [], isLoading: loadingMetrics } = useQuery({
    queryKey: ['system-metrics', selectedTimeRange],
    queryFn: async () => {
      const res = await api.get<SystemMetric[]>(`/api/v1/monitoring/metrics`, {
        params: { timerange: selectedTimeRange },
      });
      return res.data;
    },
    refetchInterval: autoRefresh ? 30000 : false, // Auto refresh every 30 seconds
  });

  // Fetch service status
  const { data: serviceStatus = [], isLoading: loadingServices } = useQuery({
    queryKey: ['service-status'],
    queryFn: async () => {
      const res = await api.get<ServiceStatus[]>(`/api/v1/monitoring/services`);
      return res.data;
    },
    refetchInterval: autoRefresh ? 15000 : false,
  });

  // Fetch active alerts
  const { data: alerts = [], isLoading: loadingAlerts } = useQuery({
    queryKey: ['monitoring-alerts'],
    queryFn: async () => {
      const res = await api.get<AlertItem[]>(`/api/v1/monitoring/alerts`, {
        params: { active: true },
      });
      return res.data;
    },
    refetchInterval: autoRefresh ? 10000 : false,
  });

  const getMetricIcon = (metricName: string) => {
    switch (metricName.toLowerCase()) {
      case 'cpu_usage':
        return <CpuChipIcon className='h-8 w-8' />;
      case 'memory_usage':
        return <CircleStackIcon className='h-8 w-8' />;
      case 'disk_usage':
        return <ServerIcon className='h-8 w-8' />;
      case 'network_io':
        return <WifiIcon className='h-8 w-8' />;
      case 'response_time':
        return <ClockIcon className='h-8 w-8' />;
      case 'throughput':
        return <BoltIcon className='h-8 w-8' />;
      default:
        return <ChartBarIcon className='h-8 w-8' />;
    }
  };

  const getMetricStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'critical':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getServiceStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800';
      case 'down':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getAlertSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-l-red-500 bg-red-50';
      case 'high':
        return 'border-l-orange-500 bg-orange-50';
      case 'medium':
        return 'border-l-yellow-500 bg-yellow-50';
      case 'low':
        return 'border-l-blue-500 bg-blue-50';
      default:
        return 'border-l-gray-500 bg-gray-50';
    }
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  if (loadingMetrics || loadingServices || loadingAlerts) {
    return (
      <div className={`flex justify-center items-center py-12 ${className}`}>
        <LoadingSpinner size='large' />
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>System Monitoring</h1>
          <p className='text-gray-600 mt-1'>
            Comprehensive system health and performance monitoring
          </p>
        </div>

        <div className='flex items-center space-x-4'>
          {/* Time Range Selector */}
          <select
            value={selectedTimeRange}
            onChange={(e) => setSelectedTimeRange(e.target.value)}
            className='px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
          >
            <option value='15m'>Last 15 minutes</option>
            <option value='1h'>Last hour</option>
            <option value='6h'>Last 6 hours</option>
            <option value='24h'>Last 24 hours</option>
            <option value='7d'>Last 7 days</option>
          </select>

          {/* Auto Refresh Toggle */}
          <label className='flex items-center'>
            <input
              type='checkbox'
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className='rounded border-gray-300 text-blue-600 focus:ring-blue-500'
            />
            <span className='ml-2 text-sm text-gray-700'>Auto-refresh</span>
          </label>

          <button
            onClick={() => window.location.reload()}
            className='flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700'
          >
            <ArrowPathIcon className='h-4 w-4' />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Alert Banner */}
      {alerts.length > 0 && (
        <div className='bg-red-50 border border-red-200 rounded-md p-4'>
          <div className='flex items-center'>
            <ExclamationTriangleIcon className='h-5 w-5 text-red-500' />
            <h3 className='ml-2 text-sm font-medium text-red-800'>
              {alerts.length} Active Alert{alerts.length !== 1 ? 's' : ''}
            </h3>
          </div>
          <div className='mt-2 text-sm text-red-700'>
            Critical issues detected. Review the alerts section below for details.
          </div>
        </div>
      )}

      {/* System Metrics Overview */}
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
        {systemMetrics.map((metric: SystemMetric) => (
          <div
            key={metric.name}
            className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'
          >
            <div className='flex items-center justify-between'>
              <div className='flex-1'>
                <div className='flex items-center'>
                  <div className={`${getMetricStatusColor(metric.status)}`}>
                    {getMetricIcon(metric.name)}
                  </div>
                  <div className='ml-3'>
                    <p className='text-sm font-medium text-gray-600'>
                      {metric.name.replace('_', ' ')}
                    </p>
                    <p className={`text-2xl font-bold ${getMetricStatusColor(metric.status)}`}>
                      {metric.value}
                      {metric.unit}
                    </p>
                  </div>
                </div>
                <div className='mt-2 flex items-center text-sm text-gray-500'>
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                      metric.status === 'healthy'
                        ? 'bg-green-100 text-green-800'
                        : metric.status === 'warning'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {metric.status}
                  </span>
                  <SignalIcon
                    className={`ml-2 h-4 w-4 ${
                      metric.trend === 'up'
                        ? 'text-green-500'
                        : metric.trend === 'down'
                          ? 'text-red-500'
                          : 'text-gray-400'
                    }`}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Service Status */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
        <div className='px-6 py-4 border-b border-gray-200'>
          <h3 className='text-lg font-medium text-gray-900'>Service Status</h3>
        </div>

        <div className='divide-y divide-gray-200'>
          {serviceStatus.map((service: ServiceStatus) => (
            <div key={service.service_name} className='px-6 py-4'>
              <div className='flex items-center justify-between'>
                <div className='flex-1'>
                  <div className='flex items-center space-x-3'>
                    <div className='flex-shrink-0'>
                      {service.status === 'healthy' ? (
                        <CheckCircleIcon className='h-6 w-6 text-green-500' />
                      ) : service.status === 'degraded' ? (
                        <ExclamationTriangleIcon className='h-6 w-6 text-yellow-500' />
                      ) : (
                        <ExclamationTriangleIcon className='h-6 w-6 text-red-500' />
                      )}
                    </div>
                    <div>
                      <h4 className='text-lg font-medium text-gray-900'>{service.service_name}</h4>
                      <div className='flex items-center space-x-4 mt-1'>
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getServiceStatusBadge(service.status)}`}
                        >
                          {service.status}
                        </span>
                        <span className='text-sm text-gray-500'>
                          Uptime: {formatUptime(service.uptime)}
                        </span>
                        <span className='text-sm text-gray-500'>
                          Response: {service.response_time}ms
                        </span>
                        {service.error_rate > 0 && (
                          <span className='text-sm text-red-600'>
                            Error rate: {service.error_rate.toFixed(2)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className='text-sm text-gray-500'>
                  Last checked: {new Date(service.last_check).toLocaleString()}
                </div>
              </div>

              {service.dependencies.length > 0 && (
                <div className='mt-3 pl-9'>
                  <p className='text-sm text-gray-600'>
                    <span className='font-medium'>Dependencies:</span>{' '}
                    {service.dependencies.join(', ')}
                  </p>
                </div>
              )}
            </div>
          ))}

          {serviceStatus.length === 0 && (
            <div className='px-6 py-8 text-center'>
              <ServerIcon className='mx-auto h-12 w-12 text-gray-400' />
              <h4 className='mt-4 text-lg font-medium text-gray-900'>No Services Monitored</h4>
              <p className='mt-2 text-gray-600'>
                Configure service monitoring to see status information
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Active Alerts */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
        <div className='px-6 py-4 border-b border-gray-200'>
          <div className='flex items-center justify-between'>
            <h3 className='text-lg font-medium text-gray-900'>Active Alerts</h3>
            <span className='text-sm text-gray-500'>{alerts.length} active</span>
          </div>
        </div>

        <div className='divide-y divide-gray-200'>
          {alerts.map((alert: AlertItem) => (
            <div
              key={alert.id}
              className={`p-6 border-l-4 ${getAlertSeverityColor(alert.severity)}`}
            >
              <div className='flex items-start justify-between'>
                <div className='flex-1'>
                  <div className='flex items-center space-x-2'>
                    <h4 className='text-lg font-medium text-gray-900'>{alert.title}</h4>
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${
                        alert.severity === 'critical'
                          ? 'bg-red-100 text-red-800 border-red-200'
                          : alert.severity === 'high'
                            ? 'bg-orange-100 text-orange-800 border-orange-200'
                            : alert.severity === 'medium'
                              ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                              : 'bg-blue-100 text-blue-800 border-blue-200'
                      }`}
                    >
                      {alert.severity}
                    </span>
                    <span className='inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700'>
                      {alert.type}
                    </span>
                  </div>
                  <p className='mt-2 text-gray-700'>{alert.description}</p>
                  <p className='mt-2 text-sm text-gray-500'>
                    {new Date(alert.timestamp).toLocaleString()}
                  </p>
                </div>

                <div className='ml-4 flex items-center space-x-2'>
                  {alert.acknowledged ? (
                    <span className='inline-flex items-center px-3 py-1 rounded-md text-sm bg-green-100 text-green-800'>
                      Acknowledged
                    </span>
                  ) : (
                    <button className='inline-flex items-center px-3 py-1 rounded-md text-sm bg-blue-100 text-blue-700 hover:bg-blue-200'>
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}

          {alerts.length === 0 && (
            <div className='px-6 py-8 text-center'>
              <CheckCircleIcon className='mx-auto h-12 w-12 text-green-500' />
              <h4 className='mt-4 text-lg font-medium text-gray-900'>No Active Alerts</h4>
              <p className='mt-2 text-gray-600'>All systems are operating normally</p>
            </div>
          )}
        </div>
      </div>

      {/* Performance Charts Placeholder */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <h3 className='text-lg font-medium text-gray-900 mb-4'>System Performance Trends</h3>
          <div className='h-64 flex items-center justify-center text-gray-500'>
            <div className='text-center'>
              <DocumentChartBarIcon className='mx-auto h-12 w-12 mb-2' />
              <p>Performance charts will be displayed here</p>
              <p className='text-sm'>Integration with monitoring backend required</p>
            </div>
          </div>
        </div>

        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <h3 className='text-lg font-medium text-gray-900 mb-4'>Network Usage</h3>
          <div className='h-64 flex items-center justify-center text-gray-500'>
            <div className='text-center'>
              <WifiIcon className='mx-auto h-12 w-12 mb-2' />
              <p>Network usage charts will be displayed here</p>
              <p className='text-sm'>Integration with network monitoring required</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
