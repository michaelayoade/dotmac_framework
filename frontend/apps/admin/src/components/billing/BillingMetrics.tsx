/**
 * Billing Metrics Component
 * Displays key billing metrics in a clean, focused component
 */

'use client';

import { type FC } from 'react';
import { 
  DollarSign, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle,
  ArrowUpIcon,
  ArrowDownIcon
} from 'lucide-react';
import { 
  AnimatedCounter,
  FadeInWhenVisible,
  StaggeredFadeIn,
  StaggerChild,
  AnimatedCard,
  PulseIndicator,
  BounceIn
} from '@dotmac/primitives/animations/Animations';
import { StatusBadge } from '@dotmac/primitives/indicators/StatusIndicators';
import { DataLoader } from '../ui/LoadingStates';
import { useMetrics } from '../../hooks/useBillingData';
import type { Metrics } from '../../types/billing';

interface MetricCardProps {
  title: string;
  value: number;
  trend?: number;
  icon: FC<{ className?: string }>;
  format?: 'currency' | 'percentage' | 'number';
}

function MetricCard({ title, value, trend, icon: Icon, format = 'currency' }: MetricCardProps) {
  const formatValue = (val: number) => {
    switch (format) {
      case 'currency':
        return `$${val.toLocaleString()}`;
      case 'percentage':
        return `${val.toFixed(1)}%`;
      default:
        return val.toLocaleString();
    }
  };

  const getTrendVariant = () => {
    if (trend === undefined) return 'pending';
    if (trend > 0) return 'online';
    if (trend < 0) return 'overdue';
    return 'pending';
  };

  return (
    <FadeInWhenVisible>
      <AnimatedCard className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <PulseIndicator active={trend !== undefined && Math.abs(trend) > 5}>
              <div className="p-2 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-lg">
                <Icon className="w-6 h-6 text-blue-600" />
              </div>
            </PulseIndicator>
            <div>
              <p className="text-sm font-medium text-gray-600">{title}</p>
              <AnimatedCounter
                value={value}
                prefix={format === 'currency' ? '$' : ''}
                suffix={format === 'percentage' ? '%' : ''}
                className="text-2xl font-bold text-gray-900"
              />
            </div>
          </div>
          {trend !== undefined && (
            <BounceIn>
              <StatusBadge
                variant={getTrendVariant()}
                size="sm"
                showDot={true}
                pulse={Math.abs(trend) > 10}
              >
                {trend > 0 ? (
                  <ArrowUpIcon className="w-3 h-3 mr-1" />
                ) : trend < 0 ? (
                  <ArrowDownIcon className="w-3 h-3 mr-1" />
                ) : null}
                {Math.abs(trend).toFixed(1)}%
              </StatusBadge>
            </BounceIn>
          )}
        </div>
      </AnimatedCard>
    </FadeInWhenVisible>
  );
}

interface BillingMetricsProps {
  period?: string;
  className?: string;
}

export function BillingMetrics({ period = '30d', className = '' }: BillingMetricsProps) {
  const { data: metrics, isLoading, error } = useMetrics(period);

  return (
    <div className={className}>
      <DataLoader
        data={metrics}
        isLoading={isLoading}
        error={error}
        isEmpty={!metrics}
        loadingFallback={<MetricsLoadingSkeleton />}
        errorFallback={(error) => <MetricsErrorFallback error={error} />}
      >
        {(metrics) => (
          <StaggeredFadeIn>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StaggerChild>
                <MetricCard
                  title="Total Revenue"
                  value={metrics.totalRevenue}
                  trend={metrics.trends.revenue}
                  icon={DollarSign}
                  format="currency"
                />
              </StaggerChild>
              
              <StaggerChild>
                <MetricCard
                  title="Monthly Recurring"
                  value={metrics.monthlyRecurring}
                  trend={metrics.trends.revenue}
                  icon={TrendingUp}
                  format="currency"
                />
              </StaggerChild>
              
              <StaggerChild>
                <MetricCard
                  title="Outstanding Amount"
                  value={metrics.outstandingAmount}
                  icon={AlertTriangle}
                  format="currency"
                />
              </StaggerChild>
              
              <StaggerChild>
                <MetricCard
                  title="Collections Rate"
                  value={metrics.collectionsRate}
                  trend={metrics.trends.collections}
                  icon={CheckCircle}
                  format="percentage"
                />
              </StaggerChild>
            </div>
          </StaggeredFadeIn>
        )}
      </DataLoader>
    </div>
  );
}

// Loading skeleton for metrics
function MetricsLoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gray-200 rounded-lg animate-pulse" />
            <div className="space-y-2 flex-1">
              <div className="h-4 bg-gray-200 rounded animate-pulse w-2/3" />
              <div className="h-6 bg-gray-200 rounded animate-pulse w-1/2" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Error fallback for metrics
function MetricsErrorFallback({ error }: { error: Error }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
      <div className="flex items-center space-x-3">
        <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />
        <div>
          <h3 className="font-medium text-red-800">Failed to Load Metrics</h3>
          <p className="text-sm text-red-600 mt-1">{error.message}</p>
          <button 
            className="text-sm text-red-800 underline mt-2 hover:no-underline"
            onClick={() => window.location.reload()}
          >
            Try refreshing the page
          </button>
        </div>
      </div>
    </div>
  );
}