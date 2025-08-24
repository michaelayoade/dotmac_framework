'use client';

import { useQuery } from '@tanstack/react-query';
import { 
  UsersIcon, 
  CreditCardIcon, 
  CloudIcon, 
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { tenantApi, billingApi, monitoringApi } from '@/lib/api';

export default function DashboardPage() {
  // Fetch dashboard data
  const { data: tenantsData, isLoading: tenantsLoading } = useQuery({
    queryKey: ['tenants', { page: 1, limit: 10 }],
    queryFn: () => tenantApi.list({ page: 1, limit: 10 }),
  });

  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: () => monitoringApi.health(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: () => monitoringApi.metrics(5),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Stats cards configuration
  const stats = [
    {
      name: 'Total Tenants',
      value: tenantsData?.total || 0,
      change: '+12%',
      changeType: 'positive',
      icon: UsersIcon,
      href: '/tenants',
    },
    {
      name: 'Active Subscriptions',
      value: '127', // This would come from API
      change: '+5%',
      changeType: 'positive',
      icon: CreditCardIcon,
      href: '/billing/subscriptions',
    },
    {
      name: 'Deployments',
      value: '89', // This would come from API
      change: '+8%',
      changeType: 'positive',
      icon: CloudIcon,
      href: '/infrastructure/deployments',
    },
    {
      name: 'System Health',
      value: healthData?.overall_status === 'healthy' ? 'Healthy' : 'Issues',
      change: healthData?.overall_status === 'healthy' ? 'All systems operational' : 'Needs attention',
      changeType: healthData?.overall_status === 'healthy' ? 'positive' : 'negative',
      icon: healthData?.overall_status === 'healthy' ? CheckCircleIcon : ExclamationTriangleIcon,
      href: '/monitoring',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-600">
          Overview of your DotMac Management Platform
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.name}
              className="card hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => window.location.href = item.href}
            >
              <div className="card-content">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <Icon className={`h-8 w-8 ${
                      item.changeType === 'positive' ? 'text-success-600' : 'text-danger-600'
                    }`} />
                  </div>
                  <div className="ml-4 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        {item.name}
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {tenantsLoading || healthLoading ? (
                          <LoadingSpinner size="small" />
                        ) : (
                          item.value
                        )}
                      </dd>
                    </dl>
                  </div>
                </div>
                <div className="mt-2">
                  <div className={`text-sm ${
                    item.changeType === 'positive' ? 'text-success-600' : 'text-danger-600'
                  }`}>
                    {item.change}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Status */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">System Status</h3>
          </div>
          <div className="card-content">
            {healthLoading ? (
              <div className="flex justify-center py-4">
                <LoadingSpinner />
              </div>
            ) : healthData ? (
              <div className="space-y-3">
                {Object.entries(healthData.checks || {}).map(([service, status]: [string, any]) => (
                  <div key={service} className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900 capitalize">
                      {service.replace('_', ' ')}
                    </span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      status.status === 'healthy' 
                        ? 'bg-success-100 text-success-800'
                        : 'bg-danger-100 text-danger-800'
                    }`}>
                      {status.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">Unable to load system status</p>
            )}
          </div>
        </div>

        {/* System Metrics */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">System Metrics</h3>
          </div>
          <div className="card-content">
            {metricsLoading ? (
              <div className="flex justify-center py-4">
                <LoadingSpinner />
              </div>
            ) : metricsData ? (
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium text-gray-900">CPU Usage</span>
                    <span className="text-gray-600">
                      {metricsData.cpu_usage_percent?.current?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="mt-1 w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full"
                      style={{ width: `${metricsData.cpu_usage_percent?.current || 0}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium text-gray-900">Memory Usage</span>
                    <span className="text-gray-600">
                      {metricsData.memory_usage_percent?.current?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="mt-1 w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-success-600 h-2 rounded-full"
                      style={{ width: `${metricsData.memory_usage_percent?.current || 0}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium text-gray-900">Disk Usage</span>
                    <span className="text-gray-600">
                      {metricsData.disk_usage_percent?.current?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="mt-1 w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-warning-600 h-2 rounded-full"
                      style={{ width: `${metricsData.disk_usage_percent?.current || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">Unable to load metrics</p>
            )}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
        </div>
        <div className="card-content">
          <div className="flow-root">
            <ul className="-mb-8">
              {/* This would be populated with real activity data */}
              <li>
                <div className="relative pb-8">
                  <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" />
                  <div className="relative flex space-x-3">
                    <div>
                      <span className="h-8 w-8 rounded-full bg-success-500 flex items-center justify-center ring-8 ring-white">
                        <CheckCircleIcon className="h-5 w-5 text-white" />
                      </span>
                    </div>
                    <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                      <div>
                        <p className="text-sm text-gray-500">
                          New tenant <span className="font-medium text-gray-900">Acme Corp</span> created
                        </p>
                      </div>
                      <div className="text-right text-sm whitespace-nowrap text-gray-500">
                        2 hours ago
                      </div>
                    </div>
                  </div>
                </div>
              </li>
              
              <li>
                <div className="relative pb-8">
                  <div className="relative flex space-x-3">
                    <div>
                      <span className="h-8 w-8 rounded-full bg-primary-500 flex items-center justify-center ring-8 ring-white">
                        <CreditCardIcon className="h-5 w-5 text-white" />
                      </span>
                    </div>
                    <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                      <div>
                        <p className="text-sm text-gray-500">
                          Billing plan <span className="font-medium text-gray-900">Enterprise</span> updated
                        </p>
                      </div>
                      <div className="text-right text-sm whitespace-nowrap text-gray-500">
                        4 hours ago
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}