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
import { useTenantAuth } from '@/components/auth/TenantAuthProvider';

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

  useEffect(() => {
    // Mock data - in production, fetch from management platform API
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

    // Simulate API call delay
    setTimeout(() => {
      setOverview(mockOverview);
      setIsLoading(false);
    }, 1000);
  }, []);

  if (isLoading || !overview) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const metrics = [
    {
      name: 'Active Customers',
      value: overview.current_customers.toLocaleString(),
      icon: Users,
      trend: { value: '+8.5%', positive: true },
      description: 'from last month',
    },
    {
      name: 'Active Services',
      value: overview.current_services.toLocaleString(),
      icon: Server,
      trend: { value: '+12.3%', positive: true },
      description: 'from last month',
    },
    {
      name: 'Storage Usage',
      value: `${overview.storage_used_gb}GB`,
      icon: HardDrive,
      trend: { value: `${Math.round((overview.storage_used_gb / overview.storage_limit_gb) * 100)}%`, positive: false },
      description: `of ${overview.storage_limit_gb}GB limit`,
    },
    {
      name: 'Monthly Cost',
      value: `$${overview.monthly_cost.toLocaleString()}`,
      icon: DollarSign,
      trend: { value: '+5.2%', positive: false },
      description: 'next billing cycle',
    },
  ];

  const healthMetrics = [
    {
      name: 'Uptime',
      value: `${overview.health_metrics.uptime_percentage}%`,
      status: overview.health_metrics.uptime_percentage >= 99.9 ? 'excellent' : 'good',
    },
    {
      name: 'Response Time',
      value: `${overview.health_metrics.avg_response_time_ms}ms`,
      status: overview.health_metrics.avg_response_time_ms < 200 ? 'excellent' : 'good',
    },
    {
      name: 'Error Rate',
      value: `${overview.health_metrics.error_rate_percentage}%`,
      status: overview.health_metrics.error_rate_percentage < 0.1 ? 'excellent' : 'warning',
    },
    {
      name: 'CPU Usage',
      value: `${overview.health_metrics.cpu_usage_percentage}%`,
      status: overview.health_metrics.cpu_usage_percentage < 70 ? 'good' : 'warning',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.name}
        </h2>
        <p className="text-gray-600">
          Here's what's happening with your {tenant?.display_name} instance today.
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((metric) => (
          <div key={metric.name} className="metric-card">
            <div className="flex items-center justify-between">
              <div>
                <div className="metric-value">{metric.value}</div>
                <div className="metric-label">{metric.name}</div>
              </div>
              <metric.icon className="h-8 w-8 text-tenant-500" />
            </div>
            <div className={`metric-trend ${metric.trend.positive ? 'positive' : 'negative'}`}>
              {metric.trend.positive ? (
                <TrendingUp className="h-4 w-4 mr-1" />
              ) : (
                <TrendingDown className="h-4 w-4 mr-1" />
              )}
              {metric.trend.value} {metric.description}
            </div>
          </div>
        ))}
      </div>

      {/* Health Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="tenant-card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Activity className="h-5 w-5 mr-2 text-tenant-500" />
            System Health
          </h3>
          <div className="space-y-4">
            {healthMetrics.map((metric) => (
              <div key={metric.name} className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-gray-900">{metric.name}</div>
                  <div className="text-sm text-gray-500">{metric.value}</div>
                </div>
                <div className="flex items-center">
                  {metric.status === 'excellent' ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : metric.status === 'good' ? (
                    <CheckCircle className="h-5 w-5 text-blue-500" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-yellow-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {overview.active_alerts > 0 && (
            <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center">
                <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
                <div>
                  <div className="text-sm font-medium text-yellow-800">
                    {overview.active_alerts} Active Alert{overview.active_alerts !== 1 ? 's' : ''}
                  </div>
                  <div className="text-sm text-yellow-700">
                    Review system alerts in the monitoring section
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="tenant-card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Clock className="h-5 w-5 mr-2 text-tenant-500" />
            Recent Activity
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div>
                <div className="text-sm font-medium text-gray-900">User Logins</div>
                <div className="text-sm text-gray-500">Last 24 hours</div>
              </div>
              <div className="text-lg font-semibold text-gray-900">
                {overview.recent_logins}
              </div>
            </div>
            
            <div className="flex items-center justify-between py-2">
              <div>
                <div className="text-sm font-medium text-gray-900">API Requests</div>
                <div className="text-sm text-gray-500">Last 24 hours</div>
              </div>
              <div className="text-lg font-semibold text-gray-900">
                {overview.recent_api_calls.toLocaleString()}
              </div>
            </div>
            
            <div className="flex items-center justify-between py-2">
              <div>
                <div className="text-sm font-medium text-gray-900">Support Tickets</div>
                <div className="text-sm text-gray-500">Open tickets</div>
              </div>
              <div className="text-lg font-semibold text-gray-900">
                {overview.recent_tickets}
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-tenant-50 border border-tenant-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-tenant-800">Next Billing</div>
                <div className="text-sm text-tenant-700">
                  {new Date(overview.next_billing_date).toLocaleDateString()}
                </div>
              </div>
              <div className="text-lg font-semibold text-tenant-900">
                ${overview.monthly_cost.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="tenant-card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="tenant-button-secondary text-left p-4 h-auto">
            <div className="font-medium">Manage Users</div>
            <div className="text-sm text-gray-500 mt-1">Add or remove user accounts</div>
          </button>
          
          <button className="tenant-button-secondary text-left p-4 h-auto">
            <div className="font-medium">View Billing</div>
            <div className="text-sm text-gray-500 mt-1">Check invoices and usage</div>
          </button>
          
          <button className="tenant-button-secondary text-left p-4 h-auto">
            <div className="font-medium">Get Support</div>
            <div className="text-sm text-gray-500 mt-1">Contact our support team</div>
          </button>
        </div>
      </div>
    </div>
  );
}