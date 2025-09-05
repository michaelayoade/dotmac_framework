'use client';

import { useQuery } from '@tanstack/react-query';
import {
  UsersIcon,
  CreditCardIcon,
  CloudIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { TenantManagement } from '@/components/tenant/TenantManagement';
import { DashboardGrid, PackageDashboardWidgets } from '@/components/adapters/DashboardComponents';
import { tenantApi, monitoringApi } from '@/lib/api';
import { useAppNavigation, routes } from '@/lib/navigation';
import { useErrorHandler } from '@/lib/error-handling';
import type { DashboardStatsResponse } from '@/types/dashboard';

export default function DashboardPage() {
  const { push } = useAppNavigation();
  const { handleRetryableError } = useErrorHandler();

  // Fetch dashboard data with real API and error handling
  const {
    data: dashboardData,
    isLoading: dashboardLoading,
    error: dashboardError,
  } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      return await handleRetryableError(
        () => monitoringApi.getDashboardStats() as Promise<DashboardStatsResponse>,
        'Dashboard Stats',
        3, // max retries
        1000, // retry delay
        {
          showNotification: false, // Don't show notification for background refresh
        }
      );
    },
    refetchInterval: 60000, // Refresh every minute
    staleTime: 30000, // Consider data stale after 30 seconds
    retry: false, // Disable React Query retry since we handle it manually
  });

  // Fetch recent tenant data for the table
  const { data: tenantsData } = useQuery({
    queryKey: ['tenants', { page: 1, limit: 5 }],
    queryFn: async () => {
      return await handleRetryableError(
        () => tenantApi.list({ page: 1, limit: 5 }),
        'Recent Tenants',
        2, // fewer retries for secondary data
        500, // shorter retry delay
        {
          showNotification: false, // Silent failure for secondary data
        }
      );
    },
    retry: false,
  });

  // Fetch system metrics for the performance section
  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: () => monitoringApi.metrics(5),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Extract data from API response or show fallback
  const stats = dashboardData?.data
    ? [
        {
          name: 'Total Tenants',
          value: dashboardData.data.tenants.total,
          change: `${dashboardData.data.tenants.trends.total.changePercent >= 0 ? '+' : ''}${dashboardData.data.tenants.trends.total.changePercent}%`,
          changeType: dashboardData.data.tenants.trends.total.changeType,
          icon: UsersIcon,
          href: routes.tenants.list,
        },
        {
          name: 'Active Subscriptions',
          value: dashboardData.data.subscriptions.active,
          change: `${dashboardData.data.subscriptions.trends.subscriptions.changePercent >= 0 ? '+' : ''}${dashboardData.data.subscriptions.trends.subscriptions.changePercent}%`,
          changeType: dashboardData.data.subscriptions.trends.subscriptions.changeType,
          icon: CreditCardIcon,
          href: routes.billing.subscriptions,
        },
        {
          name: 'Deployments',
          value: dashboardData.data.deployments.total,
          change: `${dashboardData.data.deployments.trends.deployments.changePercent >= 0 ? '+' : ''}${dashboardData.data.deployments.trends.deployments.changePercent}%`,
          changeType: dashboardData.data.deployments.trends.deployments.changeType,
          icon: CloudIcon,
          href: routes.infrastructure.deployments,
        },
        {
          name: 'System Health',
          value:
            dashboardData.data.system.health === 'healthy'
              ? 'Healthy'
              : dashboardData.data.system.health === 'warning'
                ? 'Warning'
                : 'Critical',
          change:
            dashboardData.data.system.health === 'healthy'
              ? 'All systems operational'
              : dashboardData.data.system.health === 'warning'
                ? 'Some issues detected'
                : 'Critical issues',
          changeType:
            dashboardData.data.system.health === 'healthy'
              ? 'positive'
              : dashboardData.data.system.health === 'warning'
                ? 'neutral'
                : 'negative',
          icon:
            dashboardData.data.system.health === 'healthy'
              ? CheckCircleIcon
              : ExclamationTriangleIcon,
          href: routes.monitoring,
        },
      ]
    : dashboardError
      ? [
          // Fallback stats when API fails
          {
            name: 'Total Tenants',
            value: tenantsData?.total || '—',
            change: 'Unable to load trends',
            changeType: 'neutral' as const,
            icon: UsersIcon,
            href: routes.tenants.list,
          },
          {
            name: 'Active Subscriptions',
            value: '—',
            change: 'Data unavailable',
            changeType: 'neutral' as const,
            icon: CreditCardIcon,
            href: routes.billing.subscriptions,
          },
          {
            name: 'Deployments',
            value: '—',
            change: 'Data unavailable',
            changeType: 'neutral' as const,
            icon: CloudIcon,
            href: routes.infrastructure.deployments,
          },
          {
            name: 'System Health',
            value: 'Unknown',
            change: 'Unable to check status',
            changeType: 'neutral' as const,
            icon: ExclamationTriangleIcon,
            href: routes.monitoring,
          },
        ]
      : [];

  return (
    <div className='space-y-6'>
      {/* Page Header */}
      <div>
        <h1 className='text-2xl font-bold text-gray-900'>Dashboard</h1>
        <p className='mt-1 text-sm text-gray-600'>Overview of your DotMac Management Platform</p>
      </div>

      {/* Stats Grid */}
      <DashboardGrid
        stats={stats.map((item) => ({
          ...item,
          onClick: () => push(item.href),
          loading: dashboardLoading,
        }))}
        columns={4}
        loading={dashboardLoading}
      />

      {/* Package Dashboard Widgets */}
      <div className='space-y-4'>
        <h2 className='text-lg font-medium text-gray-900'>System Overview</h2>
        <PackageDashboardWidgets layout='grid' />
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* System Status */}
        <div className='card'>
          <div className='card-header'>
            <h3 className='text-lg font-medium text-gray-900'>Recent Activity</h3>
          </div>
          <div className='card-content'>
            {dashboardLoading ? (
              <div className='flex justify-center py-4'>
                <LoadingSpinner />
              </div>
            ) : dashboardData?.data.activity ? (
              <div className='flow-root'>
                <ul className='-mb-8'>
                  {dashboardData.data.activity.map((activity, index) => (
                    <li key={activity.id}>
                      <div className='relative pb-8'>
                        {index !== dashboardData.data.activity.length - 1 && (
                          <span className='absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200' />
                        )}
                        <div className='relative flex space-x-3'>
                          <div>
                            <span
                              className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${
                                activity.severity === 'success'
                                  ? 'bg-success-500'
                                  : activity.severity === 'warning'
                                    ? 'bg-warning-500'
                                    : activity.severity === 'error'
                                      ? 'bg-danger-500'
                                      : 'bg-primary-500'
                              }`}
                            >
                              <CheckCircleIcon className='h-5 w-5 text-white' />
                            </span>
                          </div>
                          <div className='min-w-0 flex-1 pt-1.5 flex justify-between space-x-4'>
                            <div>
                              <p className='text-sm text-gray-500'>{activity.message}</p>
                            </div>
                            <div className='text-right text-sm whitespace-nowrap text-gray-500'>
                              {new Date(activity.timestamp).toLocaleDateString('en-US', {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </div>
                          </div>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className='text-gray-500 text-sm'>No recent activity</p>
            )}
          </div>
        </div>

        {/* System Metrics */}
        <div className='card'>
          <div className='card-header'>
            <h3 className='text-lg font-medium text-gray-900'>System Metrics</h3>
          </div>
          <div className='card-content'>
            {metricsLoading ? (
              <div className='flex justify-center py-4'>
                <LoadingSpinner />
              </div>
            ) : metricsData ? (
              <div className='space-y-4'>
                <div>
                  <div className='flex justify-between text-sm'>
                    <span className='font-medium text-gray-900'>CPU Usage</span>
                    <span className='text-gray-600'>
                      {metricsData.cpu_usage_percent?.current?.toFixed(1)}%
                    </span>
                  </div>
                  <div className='mt-1 w-full bg-gray-200 rounded-full h-2'>
                    <div
                      className='bg-primary-600 h-2 rounded-full'
                      style={{ width: `${metricsData.cpu_usage_percent?.current || 0}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className='flex justify-between text-sm'>
                    <span className='font-medium text-gray-900'>Memory Usage</span>
                    <span className='text-gray-600'>
                      {metricsData.memory_usage_percent?.current?.toFixed(1)}%
                    </span>
                  </div>
                  <div className='mt-1 w-full bg-gray-200 rounded-full h-2'>
                    <div
                      className='bg-success-600 h-2 rounded-full'
                      style={{ width: `${metricsData.memory_usage_percent?.current || 0}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className='flex justify-between text-sm'>
                    <span className='font-medium text-gray-900'>Disk Usage</span>
                    <span className='text-gray-600'>
                      {metricsData.disk_usage_percent?.current?.toFixed(1)}%
                    </span>
                  </div>
                  <div className='mt-1 w-full bg-gray-200 rounded-full h-2'>
                    <div
                      className='bg-warning-600 h-2 rounded-full'
                      style={{ width: `${metricsData.disk_usage_percent?.current || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <p className='text-gray-500 text-sm'>Unable to load metrics</p>
            )}
          </div>
        </div>
      </div>

      {/* Tenant Management Overview */}
      <TenantManagement showStats={false} compact={true} />
    </div>
  );
}
