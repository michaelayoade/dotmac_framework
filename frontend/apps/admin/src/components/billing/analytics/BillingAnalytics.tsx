/**
 * Billing Analytics - Focused component for financial analytics and charts
 * Handles revenue trends, collections performance, and payment method analysis
 */

'use client';

import {
  SlideIn,
  FadeInWhenVisible,
  AnimatedCounter,
  AnimatedProgressBar,
} from '@dotmac/providers/animations/Animations';
import {
  RevenueChart,
  ServiceStatusChart,
} from '@dotmac/providers/charts/InteractiveChart';
import {
  StatusBadge,
  UptimeIndicator,
  AlertSeverityIndicator,
  NetworkPerformanceIndicator,
} from '@dotmac/providers/indicators/StatusIndicators';
import type { Metrics } from '../../../types/billing';

interface BillingAnalyticsProps {
  metrics: Metrics;
}

export function BillingAnalytics({ metrics }: BillingAnalyticsProps) {
  return (
    <div className='p-6 space-y-8'>
      {/* Revenue Trend Chart */}
      <SlideIn direction='up' className='space-y-4'>
        <h3 className='text-lg font-semibold text-gray-900'>Revenue Trends</h3>
        <div className='bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4'>
          <RevenueChart
            data={metrics.chartData.revenue.map((item) => ({
              month: item.month,
              revenue: item.amount,
              target: item.amount * 1.1,
              previousYear: item.amount * 0.85,
            }))}
            height={350}
          />
        </div>
      </SlideIn>

      <div className='grid grid-cols-1 lg:grid-cols-2 gap-8'>
        {/* Collections Performance */}
        <SlideIn direction='left' delay={0.2}>
          <div className='bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-6'>
            <h3 className='text-lg font-semibold text-gray-900 mb-4'>
              Collections Performance
            </h3>
            <div className='space-y-4'>
              <div className='flex items-center justify-between'>
                <span className='text-sm font-medium text-gray-600'>Current Rate</span>
                <AnimatedCounter
                  value={metrics.collectionsRate}
                  suffix='%'
                  className='text-lg font-bold text-green-600'
                />
              </div>
              <AnimatedProgressBar
                progress={metrics.collectionsRate}
                color='bg-green-500'
                backgroundColor='bg-green-100'
                showLabel={false}
                className='mt-2'
              />
              <div className='pt-4'>
                <UptimeIndicator uptime={metrics.collectionsRate} />
              </div>
            </div>
          </div>
        </SlideIn>

        {/* Payment Methods Distribution */}
        <SlideIn direction='right' delay={0.4}>
          <div className='bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg p-6'>
            <h3 className='text-lg font-semibold text-gray-900 mb-4'>Payment Methods</h3>
            <ServiceStatusChart
              data={metrics.chartData.paymentMethods.map((method, index) => ({
                name: method.method,
                value: method.percentage,
                status:
                  index === 0
                    ? 'online'
                    : index === 1
                      ? 'online'
                      : index === 2
                        ? 'maintenance'
                        : 'offline',
              }))}
              height={250}
            />
            <div className='mt-4 space-y-3'>
              {metrics.chartData.paymentMethods.map((method, index) => (
                <FadeInWhenVisible key={method.method} delay={index * 0.1}>
                  <div className='flex items-center justify-between'>
                    <div className='flex items-center space-x-3'>
                      <StatusBadge
                        variant={
                          index === 0
                            ? 'online'
                            : index === 1
                              ? 'active'
                              : index === 2
                                ? 'maintenance'
                                : 'offline'
                        }
                        size='sm'
                      >
                        {method.method}
                      </StatusBadge>
                    </div>
                    <div className='text-right'>
                      <div className='text-sm font-semibold text-gray-900'>
                        <AnimatedCounter value={method.percentage} suffix='%' />
                      </div>
                      <div className='text-xs text-gray-500'>
                        $<AnimatedCounter value={method.amount} />
                      </div>
                    </div>
                  </div>
                </FadeInWhenVisible>
              ))}
            </div>
          </div>
        </SlideIn>
      </div>

      {/* Additional Analytics */}
      <SlideIn direction='up' delay={0.6}>
        <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
          <div className='bg-white border-2 border-dashed border-gray-200 rounded-lg p-6 text-center'>
            <AlertSeverityIndicator
              severity={
                metrics.paymentFailureRate > 5
                  ? 'error'
                  : metrics.paymentFailureRate > 2
                    ? 'warning'
                    : 'info'
              }
              message={`Payment failure rate: ${metrics.paymentFailureRate}%`}
            />
          </div>
          <div className='bg-white border-2 border-dashed border-gray-200 rounded-lg p-6'>
            <h4 className='text-sm font-medium text-gray-600 mb-3'>Average Invoice Value</h4>
            <div className='text-center'>
              <AnimatedCounter
                value={metrics.averageInvoiceValue}
                prefix='$'
                className='text-2xl font-bold text-blue-600'
              />
            </div>
          </div>
          <div className='bg-white border-2 border-dashed border-gray-200 rounded-lg p-6'>
            <NetworkPerformanceIndicator latency={15} packetLoss={0.1} bandwidth={85} />
          </div>
        </div>
      </SlideIn>
    </div>
  );
}
