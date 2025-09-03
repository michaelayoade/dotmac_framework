'use client';

import { useState, useEffect } from 'react';
import {
  Users,
  Server,
  HardDrive,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
} from 'lucide-react';
import { useTenantAuth } from '@/components/auth/TenantAuthProviderNew';
import { TenantApiService } from '@/lib/tenant-api-service';
import {
  UniversalDashboard,
  UniversalMetricCard,
  UniversalKPISection,
  UniversalActivityFeed,
} from '@dotmac/primitives';

interface HealthMetrics {
  uptime_percentage: number;
  avg_response_time_ms: number;
  error_rate_percentage: number;
  cpu_usage_percentage: number;
  memory_usage_percentage: number;
  storage_usage_percentage: number;
}

interface TenantOverview {
  current_customers: number;
  current_services: number;
  storage_used_gb: number;
  storage_limit_gb: number;
  health_metrics: HealthMetrics;
  recent_logins: number;
  recent_api_calls: number;
  recent_tickets: number;
  active_alerts: number;
  next_billing_date: string;
  monthly_cost: number;
}

export default function DashboardPage() {
  const { tenant, user } = useTenantAuth();
  const [overview, setOverview] = useState<TenantOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOverviewData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await TenantApiService.getTenantOverview();

        if (result.success && result.data) {
          setOverview(result.data);
        } else {
          // Fallback to mock data if API is unavailable
          const mockOverview: TenantOverview = {
            current_customers: 1247,
            current_services: 3891,
            storage_used_gb: 67.5,
            storage_limit_gb: 100,
            health_metrics: {
              uptime_percentage: 99.95,
              avg_response_time_ms: 185,
              error_rate_percentage: 0.02,
              cpu_usage_percentage: 45.2,
              memory_usage_percentage: 68.7,
              storage_usage_percentage: 67.5,
            },
            recent_logins: 156,
            recent_api_calls: 12450,
            recent_tickets: 2,
            active_alerts: 0,
            next_billing_date: '2024-02-15',
            monthly_cost: 2650,
          };

          setOverview(mockOverview);
          setError('Using demo data - API unavailable');
        }
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error('Dashboard data fetch failed:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchOverviewData();
  }, []);

  if (isLoading || !overview) {
    return (
      <div className='space-y-6'>
        <div className='animate-pulse'>
          <div className='h-8 bg-gray-200 rounded w-1/4 mb-6'></div>
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className='h-32 bg-gray-200 rounded-lg'></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Prepare metrics for universal components
  const kpiItems = [
    {
      id: 'customers',
      label: 'Active Customers',
      value: overview.current_customers,
      formatAs: 'number',
      trend: { value: 8.5, direction: 'up' as const },
      icon: Users,
      color: 'blue',
    },
    {
      id: 'services',
      label: 'Active Services',
      value: overview.current_services,
      formatAs: 'number',
      trend: { value: 12.3, direction: 'up' as const },
      icon: Server,
      color: 'green',
    },
    {
      id: 'storage',
      label: 'Storage Usage',
      value: overview.storage_used_gb,
      formatAs: 'storage',
      progress: { current: overview.storage_used_gb, max: overview.storage_limit_gb },
      icon: HardDrive,
      color: 'orange',
    },
    {
      id: 'cost',
      label: 'Monthly Cost',
      value: overview.monthly_cost,
      formatAs: 'currency',
      trend: { value: 5.2, direction: 'up' as const },
      icon: DollarSign,
      color: 'red',
    },
  ];

  const healthKpis = [
    {
      id: 'uptime',
      label: 'Uptime',
      value: overview.health_metrics.uptime_percentage,
      formatAs: 'percentage',
      status: overview.health_metrics.uptime_percentage >= 99.9 ? 'success' : 'warning',
    },
    {
      id: 'response_time',
      label: 'Response Time',
      value: overview.health_metrics.avg_response_time_ms,
      formatAs: 'number',
      suffix: 'ms',
      status: overview.health_metrics.avg_response_time_ms < 200 ? 'success' : 'warning',
    },
    {
      id: 'error_rate',
      label: 'Error Rate',
      value: overview.health_metrics.error_rate_percentage,
      formatAs: 'percentage',
      status: overview.health_metrics.error_rate_percentage < 0.1 ? 'success' : 'error',
    },
    {
      id: 'cpu_usage',
      label: 'CPU Usage',
      value: overview.health_metrics.cpu_usage_percentage,
      formatAs: 'percentage',
      status: overview.health_metrics.cpu_usage_percentage < 70 ? 'success' : 'warning',
    },
  ];

  const activityItems = [
    {
      id: 'logins',
      title: 'User Logins',
      description: 'Last 24 hours',
      value: overview.recent_logins,
      timestamp: new Date(),
      type: 'metric' as const,
    },
    {
      id: 'api_calls',
      title: 'API Requests',
      description: 'Last 24 hours',
      value: overview.recent_api_calls,
      timestamp: new Date(),
      type: 'metric' as const,
    },
    {
      id: 'tickets',
      title: 'Support Tickets',
      description: 'Open tickets',
      value: overview.recent_tickets,
      timestamp: new Date(),
      type: 'alert' as const,
      status: overview.recent_tickets > 0 ? 'warning' : 'success',
    },
  ];

  return (
    <UniversalDashboard
      variant='customer'
      title={`Welcome back, ${user?.name}`}
      subtitle={`Here's what's happening with your ${tenant?.display_name} instance today.`}
      user={{
        id: user?.id || '',
        name: user?.name || '',
        email: user?.email || '',
        avatar: user?.metadata?.avatar,
        role: user?.role as any,
        permissions: user?.permissions || [],
        tenantId: user?.tenantId || tenant?.id || '',
        createdAt: new Date(),
        updatedAt: new Date(),
      }}
      tenant={{
        id: tenant?.id || '',
        name: tenant?.name || '',
        displayName: tenant?.display_name || '',
        slug: tenant?.slug || '',
      }}
      alert={
        error
          ? {
              type: 'warning',
              title: 'Demo Data',
              message: error,
            }
          : undefined
      }
      className='space-y-8'
    >
      {/* Key Performance Metrics */}
      <UniversalKPISection title='Key Metrics' items={kpiItems} columns={4} className='mb-8' />

      {/* Health and Activity Grid */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8'>
        {/* System Health KPIs */}
        <div>
          <UniversalKPISection
            title='System Health'
            items={healthKpis}
            columns={2}
            showStatus
            icon={Activity}
          />

          {/* Active Alerts */}
          {overview.active_alerts > 0 && (
            <div className='mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg'>
              <div className='flex items-center'>
                <AlertTriangle className='h-5 w-5 text-yellow-600 mr-2' />
                <div>
                  <div className='text-sm font-medium text-yellow-800'>
                    {overview.active_alerts} Active Alert{overview.active_alerts !== 1 ? 's' : ''}
                  </div>
                  <div className='text-sm text-yellow-700'>
                    Review system alerts in the monitoring section
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div>
          <UniversalActivityFeed
            title='Recent Activity'
            items={activityItems}
            showTimestamp={false}
            icon={Clock}
          />

          {/* Billing Info */}
          <div className='mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg'>
            <div className='flex items-center justify-between'>
              <div>
                <div className='text-sm font-medium text-blue-800'>Next Billing</div>
                <div className='text-sm text-blue-700'>
                  {new Date(overview.next_billing_date).toLocaleDateString()}
                </div>
              </div>
              <div className='text-lg font-semibold text-blue-900'>
                ${overview.monthly_cost.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions - can be converted to universal component later */}
      <div className='bg-white rounded-lg shadow p-6'>
        <h3 className='text-lg font-semibold text-gray-900 mb-4'>Quick Actions</h3>
        <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
          <button className='bg-gray-50 hover:bg-gray-100 transition-colors rounded-lg text-left p-4 border border-gray-200'>
            <div className='font-medium'>Manage Users</div>
            <div className='text-sm text-gray-500 mt-1'>Add or remove user accounts</div>
          </button>

          <button className='bg-gray-50 hover:bg-gray-100 transition-colors rounded-lg text-left p-4 border border-gray-200'>
            <div className='font-medium'>View Billing</div>
            <div className='text-sm text-gray-500 mt-1'>Check invoices and usage</div>
          </button>

          <button className='bg-gray-50 hover:bg-gray-100 transition-colors rounded-lg text-left p-4 border border-gray-200'>
            <div className='font-medium'>Get Support</div>
            <div className='text-sm text-gray-500 mt-1'>Contact our support team</div>
          </button>
        </div>
      </div>
    </UniversalDashboard>
  );
}
