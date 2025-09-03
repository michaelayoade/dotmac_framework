/**
 * Unified Dashboard Example
 * Shows how to use all the DRY packages together
 */

import React from 'react';
import {
  UniversalMetricsGrid,
  UniversalLineChart,
  UniversalBarChart,
  ChartContainer,
  MetricData,
} from '@dotmac/dashboard';
import { formatCurrency, formatPercent, formatNumber } from '@dotmac/utils';
import {
  Users,
  TrendingUp,
  DollarSign,
  MapPin,
  Activity,
  Clock,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';

interface UnifiedDashboardProps {
  data?: {
    partners: number;
    revenue: number;
    commissions: number;
    territories: number;
    growth: number;
    alerts: number;
    performance?: any[];
    trends?: any[];
  };
}

export function UnifiedDashboard({ data }: UnifiedDashboardProps) {
  // Transform data using unified formatters
  const metrics: MetricData[] = [
    {
      name: 'Active Partners',
      value: formatNumber(data?.partners || 0),
      icon: Users,
      trend: {
        value: '+12.3%',
        positive: true,
      },
      description: 'this month',
    },
    {
      name: 'Total Revenue',
      value: formatCurrency(data?.revenue || 0),
      icon: TrendingUp,
      trend: {
        value: formatPercent(data?.growth || 0),
        positive: (data?.growth || 0) > 0,
      },
      description: 'year to date',
    },
    {
      name: 'Commission Payouts',
      value: formatCurrency(data?.commissions || 0),
      icon: DollarSign,
      trend: {
        value: '+8.7%',
        positive: true,
      },
      description: 'total earned',
    },
    {
      name: 'Territory Coverage',
      value: `${data?.territories || 0}`,
      icon: MapPin,
      trend: {
        value: '+2 new',
        positive: true,
      },
      description: 'active territories',
    },
    {
      name: 'System Status',
      value: '99.9%',
      icon: Activity,
      trend: {
        value: 'Excellent',
        positive: true,
      },
      description: 'uptime',
    },
    {
      name: 'Pending Tasks',
      value: formatNumber(data?.alerts || 0),
      icon: Clock,
      color: data?.alerts && data.alerts > 0 ? 'warning' : 'success',
      description: 'require attention',
    },
  ];

  const performanceData = data?.performance || [
    { name: 'Jan', value: 4000 },
    { name: 'Feb', value: 3000 },
    { name: 'Mar', value: 2000 },
    { name: 'Apr', value: 2780 },
    { name: 'May', value: 1890 },
    { name: 'Jun', value: 2390 },
  ];

  const trendsData = data?.trends || [
    { name: 'Q1', partners: 24, revenue: 85000 },
    { name: 'Q2', partners: 32, revenue: 95000 },
    { name: 'Q3', partners: 28, revenue: 88000 },
    { name: 'Q4', partners: 35, revenue: 102000 },
  ];

  return (
    <div className='space-y-6'>
      {/* Page Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold text-gray-900'>Reseller Management</h1>
          <p className='text-gray-600 mt-2'>Monitor your partner network performance and growth</p>
        </div>

        <div className='flex items-center space-x-2'>
          <div className='flex items-center space-x-1 text-green-600'>
            <CheckCircle className='h-4 w-4' />
            <span className='text-sm font-medium'>All Systems Operational</span>
          </div>
        </div>
      </div>

      {/* Unified Metrics Grid */}
      <UniversalMetricsGrid
        metrics={metrics}
        portal='management'
        columns={3}
        size='md'
        isLoading={!data}
      />

      {/* Charts Section */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        <ChartContainer title='Performance Trends'>
          <UniversalLineChart
            data={performanceData}
            dataKey='value'
            portal='management'
            height={300}
            showDots={true}
            showLegend={false}
          />
        </ChartContainer>

        <ChartContainer title='Partner Growth'>
          <UniversalBarChart
            data={trendsData}
            dataKey='partners'
            portal='management'
            height={300}
            showLegend={false}
          />
        </ChartContainer>
      </div>

      {/* Revenue Analysis */}
      <ChartContainer title='Revenue Analysis' className='lg:col-span-2'>
        <UniversalLineChart
          data={trendsData}
          dataKey='revenue'
          portal='management'
          height={400}
          showDots={true}
          showLegend={true}
        />
      </ChartContainer>

      {/* Quick Actions */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
        <h3 className='text-lg font-semibold text-gray-900 mb-4'>Quick Actions</h3>
        <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
          <button className='p-4 text-center hover:bg-gray-50 rounded-lg border border-gray-200'>
            <Users className='h-6 w-6 mx-auto mb-2 text-management-600' />
            <span className='text-sm font-medium'>Add Partner</span>
          </button>
          <button className='p-4 text-center hover:bg-gray-50 rounded-lg border border-gray-200'>
            <DollarSign className='h-6 w-6 mx-auto mb-2 text-management-600' />
            <span className='text-sm font-medium'>Process Payouts</span>
          </button>
          <button className='p-4 text-center hover:bg-gray-50 rounded-lg border border-gray-200'>
            <MapPin className='h-6 w-6 mx-auto mb-2 text-management-600' />
            <span className='text-sm font-medium'>Manage Territories</span>
          </button>
          <button className='p-4 text-center hover:bg-gray-50 rounded-lg border border-gray-200'>
            <TrendingUp className='h-6 w-6 mx-auto mb-2 text-management-600' />
            <span className='text-sm font-medium'>View Reports</span>
          </button>
        </div>
      </div>
    </div>
  );
}
