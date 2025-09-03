/**
 * API Gateway Dashboard - Traffic monitoring and analytics
 * Follows DRY patterns from primitives and dashboard packages
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  UniversalChart,
  UniversalMetricCard,
  UniversalKPISection,
  UniversalDashboard,
} from '@dotmac/primitives';
import { useApiGateway, useApiSubscription } from '@dotmac/auth-system';
import { monitoring } from '@dotmac/monitoring';

interface GatewayMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  requestsPerSecond: number;
  errorRate: number;
  topEndpoints: Array<{
    endpoint: string;
    requests: number;
    avgResponseTime: number;
    errorRate: number;
  }>;
  statusCodeDistribution: Record<string, number>;
  hourlyTraffic: Array<{
    hour: string;
    requests: number;
    errors: number;
    avgResponseTime: number;
  }>;
}

interface ApiGatewayDashboardProps {
  timeRange?: '1h' | '24h' | '7d' | '30d';
  refreshInterval?: number;
  showDetailedMetrics?: boolean;
  className?: string;
}

export const ApiGatewayDashboard: React.FC<ApiGatewayDashboardProps> = ({
  timeRange = '24h',
  refreshInterval = 30000,
  showDetailedMetrics = true,
  className,
}) => {
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null);
  const [alertsEnabled, setAlertsEnabled] = useState(true);

  const { isHealthy, services, getStatus } = useApiGateway();

  // Real-time metrics subscription
  const {
    data: metrics,
    loading: metricsLoading,
    error: metricsError,
  } = useApiSubscription<GatewayMetrics>(`/api/gateway/metrics?range=${timeRange}`, {
    interval: refreshInterval,
    enabled: true,
    onData: (data) => {
      // Record dashboard interaction
      monitoring.recordInteraction({
        event: 'gateway_metrics_updated',
        target: 'dashboard',
        metadata: {
          timeRange,
          totalRequests: data.totalRequests,
          errorRate: data.errorRate,
        },
      });

      // Check for alerts
      if (alertsEnabled && data.errorRate > 5) {
        monitoring.recordBusinessMetric({
          metric: 'gateway_high_error_rate_alert',
          value: data.errorRate,
          dimensions: {
            timeRange,
            threshold: '5',
          },
        });
      }
    },
  });

  // Calculate KPI metrics
  const kpiMetrics = useMemo(() => {
    if (!metrics) return [];

    const successRate = (metrics.successfulRequests / metrics.totalRequests) * 100 || 0;

    return [
      {
        label: 'Total Requests',
        value: metrics.totalRequests.toLocaleString(),
        change: '+12%', // Would be calculated from historical data
        trend: 'up' as const,
        status: 'success' as const,
      },
      {
        label: 'Success Rate',
        value: `${successRate.toFixed(1)}%`,
        change: '+0.5%',
        trend: 'up' as const,
        status: successRate > 95 ? ('success' as const) : ('warning' as const),
      },
      {
        label: 'Avg Response Time',
        value: `${metrics.averageResponseTime}ms`,
        change: '-15ms',
        trend: 'down' as const,
        status: metrics.averageResponseTime < 200 ? ('success' as const) : ('warning' as const),
      },
      {
        label: 'Requests/Second',
        value: metrics.requestsPerSecond.toFixed(1),
        change: '+8%',
        trend: 'up' as const,
        status: 'info' as const,
      },
      {
        label: 'Error Rate',
        value: `${metrics.errorRate.toFixed(2)}%`,
        change: '-1.2%',
        trend: 'down' as const,
        status: metrics.errorRate < 1 ? ('success' as const) : ('error' as const),
      },
      {
        label: 'Active Services',
        value: services.filter((s) => s.status === 'healthy').length.toString(),
        change: `${services.length} total`,
        trend: 'stable' as const,
        status: isHealthy ? ('success' as const) : ('warning' as const),
      },
    ];
  }, [metrics, services, isHealthy]);

  // Chart data for traffic visualization
  const trafficChartData = useMemo(() => {
    if (!metrics?.hourlyTraffic) return [];

    return {
      labels: metrics.hourlyTraffic.map((h) => h.hour),
      datasets: [
        {
          label: 'Requests',
          data: metrics.hourlyTraffic.map((h) => h.requests),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
        },
        {
          label: 'Errors',
          data: metrics.hourlyTraffic.map((h) => h.errors),
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          fill: true,
        },
      ],
    };
  }, [metrics?.hourlyTraffic]);

  // Response time chart data
  const responseTimeChartData = useMemo(() => {
    if (!metrics?.hourlyTraffic) return [];

    return {
      labels: metrics.hourlyTraffic.map((h) => h.hour),
      datasets: [
        {
          label: 'Avg Response Time (ms)',
          data: metrics.hourlyTraffic.map((h) => h.avgResponseTime),
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          fill: true,
        },
      ],
    };
  }, [metrics?.hourlyTraffic]);

  // Status code distribution chart
  const statusCodeChartData = useMemo(() => {
    if (!metrics?.statusCodeDistribution) return [];

    const labels = Object.keys(metrics.statusCodeDistribution);
    const data = Object.values(metrics.statusCodeDistribution);

    return {
      labels,
      datasets: [
        {
          data,
          backgroundColor: [
            'rgb(34, 197, 94)', // 2xx - green
            'rgb(59, 130, 246)', // 3xx - blue
            'rgb(245, 158, 11)', // 4xx - yellow
            'rgb(239, 68, 68)', // 5xx - red
          ],
        },
      ],
    };
  }, [metrics?.statusCodeDistribution]);

  // Top endpoints table data
  const topEndpointsData = useMemo(() => {
    if (!metrics?.topEndpoints) return [];

    return metrics.topEndpoints.map((endpoint) => ({
      endpoint: endpoint.endpoint,
      requests: endpoint.requests.toLocaleString(),
      avgResponseTime: `${endpoint.avgResponseTime}ms`,
      errorRate: `${endpoint.errorRate.toFixed(2)}%`,
      status: endpoint.errorRate < 1 ? 'success' : endpoint.errorRate < 5 ? 'warning' : 'error',
    }));
  }, [metrics?.topEndpoints]);

  const handleTimeRangeChange = (newRange: string) => {
    monitoring.recordInteraction({
      event: 'time_range_changed',
      target: 'gateway_dashboard',
      metadata: {
        previousRange: timeRange,
        newRange,
      },
    });
  };

  const handleEndpointSelect = (endpoint: string) => {
    setSelectedEndpoint(endpoint === selectedEndpoint ? null : endpoint);

    monitoring.recordInteraction({
      event: 'endpoint_selected',
      target: 'gateway_dashboard',
      metadata: {
        endpoint,
        action: endpoint === selectedEndpoint ? 'deselect' : 'select',
      },
    });
  };

  const handleExportData = () => {
    if (!metrics) return;

    const exportData = {
      timestamp: new Date().toISOString(),
      timeRange,
      metrics,
      services,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gateway-metrics-${timeRange}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    monitoring.recordInteraction({
      event: 'metrics_exported',
      target: 'gateway_dashboard',
      metadata: {
        timeRange,
        format: 'json',
      },
    });
  };

  if (metricsError) {
    return (
      <div className={`p-6 ${className}`}>
        <div className='bg-red-50 border border-red-200 rounded-lg p-4'>
          <h3 className='text-lg font-medium text-red-800'>Error Loading Metrics</h3>
          <p className='text-red-600 mt-1'>{metricsError}</p>
        </div>
      </div>
    );
  }

  return (
    <UniversalDashboard
      title='API Gateway Dashboard'
      subtitle='Real-time traffic monitoring and analytics'
      className={className}
      actions={[
        {
          label: 'Export Data',
          onClick: handleExportData,
          variant: 'secondary',
        },
        {
          label: alertsEnabled ? 'Disable Alerts' : 'Enable Alerts',
          onClick: () => setAlertsEnabled(!alertsEnabled),
          variant: alertsEnabled ? 'danger' : 'success',
        },
      ]}
      filters={[
        {
          type: 'select',
          label: 'Time Range',
          value: timeRange,
          options: [
            { label: '1 Hour', value: '1h' },
            { label: '24 Hours', value: '24h' },
            { label: '7 Days', value: '7d' },
            { label: '30 Days', value: '30d' },
          ],
          onChange: handleTimeRangeChange,
        },
      ]}
    >
      {/* KPI Section */}
      <UniversalKPISection
        metrics={kpiMetrics}
        loading={metricsLoading}
        columns={3}
        className='mb-6'
      />

      {/* Traffic Charts */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6'>
        <UniversalChart
          title='API Traffic Over Time'
          type='line'
          data={trafficChartData}
          loading={metricsLoading}
          height={300}
          options={{
            responsive: true,
            interaction: {
              mode: 'index' as const,
              intersect: false,
            },
            scales: {
              x: {
                display: true,
                title: {
                  display: true,
                  text: 'Time',
                },
              },
              y: {
                display: true,
                title: {
                  display: true,
                  text: 'Requests',
                },
              },
            },
          }}
        />

        <UniversalChart
          title='Response Time Trends'
          type='line'
          data={responseTimeChartData}
          loading={metricsLoading}
          height={300}
          options={{
            responsive: true,
            scales: {
              y: {
                beginAtZero: true,
                title: {
                  display: true,
                  text: 'Response Time (ms)',
                },
              },
            },
          }}
        />
      </div>

      {/* Status Code Distribution */}
      <div className='grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6'>
        <div className='lg:col-span-1'>
          <UniversalChart
            title='Status Code Distribution'
            type='doughnut'
            data={statusCodeChartData}
            loading={metricsLoading}
            height={250}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'bottom' as const,
                },
              },
            }}
          />
        </div>

        {/* Service Health Status */}
        <div className='lg:col-span-2'>
          <div className='bg-white rounded-lg border border-gray-200 p-6'>
            <h3 className='text-lg font-medium text-gray-900 mb-4'>Service Health</h3>
            <div className='space-y-3'>
              {services.map((service) => (
                <div
                  key={service.name}
                  className='flex items-center justify-between p-3 bg-gray-50 rounded-lg'
                >
                  <div className='flex items-center space-x-3'>
                    <div
                      className={`w-3 h-3 rounded-full ${
                        service.status === 'healthy'
                          ? 'bg-green-400'
                          : service.status === 'degraded'
                            ? 'bg-yellow-400'
                            : 'bg-red-400'
                      }`}
                    />
                    <div>
                      <p className='text-sm font-medium text-gray-900'>{service.name}</p>
                      <p className='text-xs text-gray-500'>{service.url}</p>
                    </div>
                  </div>
                  <div className='text-right'>
                    <p className='text-sm font-medium text-gray-900'>{service.responseTime}ms</p>
                    <p className='text-xs text-gray-500'>
                      {service.status.charAt(0).toUpperCase() + service.status.slice(1)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Top Endpoints Table */}
      {showDetailedMetrics && (
        <div className='bg-white rounded-lg border border-gray-200'>
          <div className='px-6 py-4 border-b border-gray-200'>
            <h3 className='text-lg font-medium text-gray-900'>Top Endpoints</h3>
            <p className='text-sm text-gray-500'>Most active API endpoints by request volume</p>
          </div>
          <div className='overflow-x-auto'>
            <table className='min-w-full divide-y divide-gray-200'>
              <thead className='bg-gray-50'>
                <tr>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Endpoint
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Requests
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Avg Response Time
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Error Rate
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className='bg-white divide-y divide-gray-200'>
                {topEndpointsData.map((endpoint, index) => (
                  <tr
                    key={index}
                    className={`hover:bg-gray-50 cursor-pointer ${
                      selectedEndpoint === endpoint.endpoint ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => handleEndpointSelect(endpoint.endpoint)}
                  >
                    <td className='px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900'>
                      {endpoint.endpoint}
                    </td>
                    <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-500'>
                      {endpoint.requests}
                    </td>
                    <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-500'>
                      {endpoint.avgResponseTime}
                    </td>
                    <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-500'>
                      {endpoint.errorRate}
                    </td>
                    <td className='px-6 py-4 whitespace-nowrap'>
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          endpoint.status === 'success'
                            ? 'bg-green-100 text-green-800'
                            : endpoint.status === 'warning'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {endpoint.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </UniversalDashboard>
  );
};

export default ApiGatewayDashboard;
