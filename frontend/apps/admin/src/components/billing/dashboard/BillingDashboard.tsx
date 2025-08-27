/**
 * Billing Dashboard - Key Metrics Overview
 * Focused component for displaying billing metrics and KPIs
 */

'use client';

import { 
  DollarSignIcon, 
  TrendingUpIcon, 
  AlertTriangleIcon, 
  CheckCircleIcon,
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
  BounceIn,
} from '@dotmac/primitives/animations/Animations';
import { StatusBadge } from '@dotmac/primitives/indicators/StatusIndicators';
import type { Metrics } from '../../../types/billing';

interface BillingDashboardProps {
  metrics: Metrics;
}

export function BillingDashboard({ metrics }: BillingDashboardProps) {
  return (
    <StaggeredFadeIn>
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
        <StaggerChild>
          <MetricCard
            title='Total Revenue'
            value={metrics.totalRevenue}
            trend={metrics.trends.revenue}
            icon={DollarSignIcon}
            format='currency'
          />
        </StaggerChild>
        <StaggerChild>
          <MetricCard
            title='Monthly Recurring'
            value={metrics.monthlyRecurring}
            trend={metrics.trends.revenue}
            icon={TrendingUpIcon}
            format='currency'
          />
        </StaggerChild>
        <StaggerChild>
          <MetricCard
            title='Outstanding Amount'
            value={metrics.outstandingAmount}
            icon={AlertTriangleIcon}
            format='currency'
          />
        </StaggerChild>
        <StaggerChild>
          <MetricCard
            title='Collections Rate'
            value={metrics.collectionsRate}
            trend={metrics.trends.collections}
            icon={CheckCircleIcon}
            format='percentage'
          />
        </StaggerChild>
      </div>
    </StaggeredFadeIn>
  );
}

interface MetricCardProps {
  title: string;
  value: number;
  trend?: number;
  icon: any;
  format?: 'currency' | 'percentage' | 'number';
}

function MetricCard({
  title,
  value,
  trend,
  icon: Icon,
  format = 'currency',
}: MetricCardProps) {
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

  return (
    <FadeInWhenVisible>
      <AnimatedCard className='bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow'>
        <div className='flex items-center justify-between'>
          <div className='flex items-center space-x-3'>
            <PulseIndicator active={trend !== undefined && Math.abs(trend) > 5}>
              <div className='p-2 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-lg'>
                <Icon className='w-6 h-6 text-blue-600' />
              </div>
            </PulseIndicator>
            <div>
              <p className='text-sm font-medium text-gray-600'>{title}</p>
              <AnimatedCounter
                value={value}
                prefix={format === 'currency' ? '$' : ''}
                suffix={format === 'percentage' ? '%' : ''}
                className='text-2xl font-bold text-gray-900'
              />
            </div>
          </div>
          {trend !== undefined && (
            <BounceIn>
              <StatusBadge
                variant={trend > 0 ? 'online' : trend < 0 ? 'overdue' : 'pending'}
                size='sm'
                showDot={true}
                pulse={Math.abs(trend) > 10}
              >
                {trend > 0 ? (
                  <ArrowUpIcon className='w-3 h-3 mr-1' />
                ) : trend < 0 ? (
                  <ArrowDownIcon className='w-3 h-3 mr-1' />
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