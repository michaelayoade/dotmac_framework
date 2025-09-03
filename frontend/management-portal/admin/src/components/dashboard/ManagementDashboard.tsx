'use client';

import { useQuery } from '@tanstack/react-query';
import {
  UsersIcon,
  BuildingOfficeIcon,
  ChartBarIcon,
  CogIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { monitoringApi, tenantApi, userApi, tenantAdminApi } from '@/lib/api';

interface DashboardStats {
  totalTenants: number;
  activeTenants: number;
  totalUsers: number;
  systemHealth: 'healthy' | 'warning' | 'critical';
  recentActivity: Array<{
    id: string;
    type: string;
    message: string;
    timestamp: string;
  }>;
}

function DashboardMetricsCard({
  title,
  value,
  icon: Icon,
  trend,
  color = 'blue',
}: {
  title: string;
  value: string | number;
  icon: any;
  trend?: string;
  color?: 'blue' | 'green' | 'yellow' | 'red';
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    yellow: 'bg-yellow-50 text-yellow-600 border-yellow-200',
    red: 'bg-red-50 text-red-600 border-red-200',
  };

  return (
    <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
      <div className='flex items-center justify-between'>
        <div>
          <p className='text-sm text-gray-600'>{title}</p>
          <p className='text-2xl font-bold text-gray-900 mt-1'>{value}</p>
          {trend && <p className='text-xs text-gray-500 mt-1'>{trend}</p>}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className='h-6 w-6' />
        </div>
      </div>
    </div>
  );
}

function SystemHealthIndicator({ status }: { status: 'healthy' | 'warning' | 'critical' }) {
  const config = {
    healthy: {
      icon: CheckCircleIcon,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      text: 'All Systems Operational',
    },
    warning: {
      icon: ExclamationTriangleIcon,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
      text: 'Minor Issues Detected',
    },
    critical: {
      icon: ExclamationTriangleIcon,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
      text: 'Critical Issues Detected',
    },
  };

  const { icon: Icon, color, bgColor, text } = config[status];

  return (
    <div
      className={`inline-flex items-center px-3 py-2 rounded-full text-sm font-medium ${color} ${bgColor}`}
    >
      <Icon className='h-4 w-4 mr-2' />
      {text}
    </div>
  );
}

function RecentActivityFeed({ activities }: { activities: any[] }) {
  if (!activities || activities.length === 0) {
    return (
      <div className='text-center py-8 text-gray-500'>
        <p>No recent activity</p>
      </div>
    );
  }

  return (
    <div className='space-y-4'>
      {activities.slice(0, 5).map((activity, index) => (
        <div key={activity.id || index} className='flex items-start space-x-3'>
          <div className='w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0'></div>
          <div className='flex-1 min-w-0'>
            <p className='text-sm text-gray-900'>{activity.message || activity.type}</p>
            <p className='text-xs text-gray-500'>
              {activity.timestamp ? new Date(activity.timestamp).toLocaleString() : 'Recently'}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function ManagementDashboard() {
  // Fetch dashboard data from multiple endpoints
  const { data: systemHealth, isLoading: healthLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: () => monitoringApi.health(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: dashboardStats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => monitoringApi.getDashboardStats(),
    refetchInterval: 60000, // Refresh every minute
  });

  const { data: tenantsData, isLoading: tenantsLoading } = useQuery({
    queryKey: ['tenants-summary'],
    queryFn: () => tenantApi.list({ limit: 5 }),
  });

  const { data: systemOverview, isLoading: overviewLoading } = useQuery({
    queryKey: ['system-overview'],
    queryFn: () => monitoringApi.getSystemOverview(),
    refetchInterval: 60000,
  });

  const isLoading = healthLoading || statsLoading || tenantsLoading || overviewLoading;

  if (isLoading) {
    return (
      <div className='space-y-6'>
        <div className='animate-pulse'>
          <div className='h-8 bg-gray-200 rounded w-1/3 mb-6'></div>
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8'>
            {[...Array(4)].map((_, i) => (
              <div key={i} className='h-24 bg-gray-200 rounded'></div>
            ))}
          </div>
          <div className='h-96 bg-gray-200 rounded'></div>
        </div>
      </div>
    );
  }

  // Extract metrics from API responses with fallbacks
  const totalTenants = tenantsData?.total || dashboardStats?.data?.tenants_count || 0;
  const activeTenants =
    tenantsData?.tenants?.filter((t: any) => t.status === 'ACTIVE').length ||
    dashboardStats?.data?.active_tenants ||
    0;
  const totalUsers = dashboardStats?.data?.users_count || systemOverview?.data?.total_users || 0;
  const healthStatus = systemHealth?.success ? 'healthy' : 'warning';
  const recentActivity = systemOverview?.data?.recent_activity || [];

  return (
    <div className='space-y-6'>
      {/* Page Header */}
      <div className='flex justify-between items-center'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Management Dashboard</h1>
          <p className='text-gray-600'>Multi-tenant platform overview and system monitoring</p>
        </div>
        <SystemHealthIndicator status={healthStatus} />
      </div>

      {/* Key Metrics */}
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
        <DashboardMetricsCard
          title='Total Tenants'
          value={totalTenants}
          icon={BuildingOfficeIcon}
          trend={`${activeTenants} active`}
          color='blue'
        />
        <DashboardMetricsCard
          title='Active Tenants'
          value={activeTenants}
          icon={CheckCircleIcon}
          trend={`${Math.round((activeTenants / totalTenants) * 100) || 0}% of total`}
          color='green'
        />
        <DashboardMetricsCard
          title='Total Users'
          value={totalUsers}
          icon={UsersIcon}
          trend='Across all tenants'
          color='blue'
        />
        <DashboardMetricsCard
          title='System Status'
          value={healthStatus === 'healthy' ? 'Healthy' : 'Issues'}
          icon={CogIcon}
          trend='Last checked now'
          color={healthStatus === 'healthy' ? 'green' : 'yellow'}
        />
      </div>

      {/* Content Grid */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Recent Tenants */}
        <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
          <div className='p-6 border-b border-gray-200'>
            <h3 className='text-lg font-semibold text-gray-900'>Recent Tenants</h3>
            <p className='text-sm text-gray-600'>Latest tenant registrations and updates</p>
          </div>
          <div className='p-6'>
            {tenantsData?.tenants && tenantsData.tenants.length > 0 ? (
              <div className='space-y-4'>
                {tenantsData.tenants.slice(0, 5).map((tenant: any) => (
                  <div key={tenant.id} className='flex items-center justify-between'>
                    <div>
                      <p className='font-medium text-gray-900'>{tenant.name}</p>
                      <p className='text-sm text-gray-500'>{tenant.subdomain}</p>
                    </div>
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                        tenant.status === 'ACTIVE'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {tenant.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className='text-gray-500 text-center py-8'>No tenants found</p>
            )}
          </div>
        </div>

        {/* System Activity */}
        <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
          <div className='p-6 border-b border-gray-200'>
            <h3 className='text-lg font-semibold text-gray-900'>Recent Activity</h3>
            <p className='text-sm text-gray-600'>System events and tenant activities</p>
          </div>
          <div className='p-6'>
            <RecentActivityFeed activities={recentActivity} />
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
        <div className='p-6 border-b border-gray-200'>
          <h3 className='text-lg font-semibold text-gray-900'>Quick Actions</h3>
        </div>
        <div className='p-6'>
          <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
            <button
              onClick={() => (window.location.href = '/tenants/new')}
              className='flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors'
            >
              <BuildingOfficeIcon className='h-5 w-5 mr-2' />
              Create New Tenant
            </button>
            <button
              onClick={() => (window.location.href = '/tenants')}
              className='flex items-center justify-center px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors'
            >
              <ChartBarIcon className='h-5 w-5 mr-2' />
              View All Tenants
            </button>
            <button
              onClick={() => (window.location.href = '/settings')}
              className='flex items-center justify-center px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors'
            >
              <CogIcon className='h-5 w-5 mr-2' />
              System Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
