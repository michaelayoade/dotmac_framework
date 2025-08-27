/**
 * Metrics Grid Component
 * Extracted from the main dashboard for better modularity
 */

import React from 'react';
import { Users, TrendingUp, DollarSign, MapPin, LucideIcon } from 'lucide-react';

export interface MetricData {
  name: string;
  value: string;
  total?: string;
  icon: LucideIcon;
  trend: {
    value: string;
    positive: boolean;
  };
  description: string;
}

interface MetricsGridProps {
  metrics: MetricData[];
  isLoading?: boolean;
}

export function MetricsGrid({ metrics, isLoading }: MetricsGridProps) {
  if (isLoading) {
    return <MetricsGridSkeleton />;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {metrics.map((metric) => (
        <MetricCard key={metric.name} metric={metric} />
      ))}
    </div>
  );
}

function MetricCard({ metric }: { metric: MetricData }) {
  const Icon = metric.icon;

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Icon className="h-8 w-8 text-management-600" />
          <div className="ml-4">
            <h3 className="text-sm font-medium text-gray-600">{metric.name}</h3>
            <div className="flex items-baseline">
              <p className="text-2xl font-semibold text-gray-900">{metric.value}</p>
              {metric.total && (
                <p className="ml-2 text-sm text-gray-500">/{metric.total}</p>
              )}
            </div>
          </div>
        </div>
      </div>
      
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center">
          <span
            className={`text-sm font-medium ${
              metric.trend.positive ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {metric.trend.value}
          </span>
          <span className="ml-2 text-sm text-gray-500">{metric.description}</span>
        </div>
      </div>
    </div>
  );
}

function MetricsGridSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="animate-pulse">
            <div className="flex items-center">
              <div className="h-8 w-8 bg-gray-300 rounded"></div>
              <div className="ml-4">
                <div className="h-4 bg-gray-300 rounded w-20 mb-2"></div>
                <div className="h-6 bg-gray-300 rounded w-16"></div>
              </div>
            </div>
            <div className="mt-4">
              <div className="h-3 bg-gray-300 rounded w-24"></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Utility function to format metrics for display
 */
export function formatMetricsData(data: any) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercent = (value: number) => `${value.toFixed(1)}%`;

  return [
    {
      name: 'Active Partners',
      value: data.active_partners?.toLocaleString() || '0',
      total: data.total_partners?.toLocaleString() || '0',
      icon: Users,
      trend: { value: '+12.3%', positive: true },
      description: `of ${data.total_partners || 0} total`,
    },
    {
      name: 'Total Revenue',
      value: formatCurrency(data.total_revenue || 0),
      icon: TrendingUp,
      trend: { value: '+18.7%', positive: true },
      description: 'this period',
    },
    {
      name: 'Commission Payout',
      value: formatCurrency(data.commission_payout || 0),
      icon: DollarSign,
      trend: { value: '-5.2%', positive: false },
      description: 'total commissions',
    },
    {
      name: 'Territory Coverage',
      value: formatPercent(data.territory_coverage || 0),
      icon: MapPin,
      trend: { value: '+3.1%', positive: true },
      description: 'geographic coverage',
    },
  ];
}