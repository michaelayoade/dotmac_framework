'use client';

import {
  ArrowUpIcon,
  ArrowDownIcon,
  UsersIcon,
  WifiIcon,
  DollarSignIcon,
  TicketIcon,
  ServerIcon,
  TrendingUpIcon,
  AlertTriangleIcon,
  Activity,
} from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts';
import { useEffect, useState } from 'react';

interface MetricsData {
  totalCustomers: number;
  activeServices: number;
  monthlyRevenue: number;
  ticketsOpen: number;
  networkHealth: number;
  bandwidthUsage: number;
  revenueGrowth: number;
  customerSatisfaction: number;
  growth: {
    customers: number;
    revenue: number;
    services: number;
    tickets: number;
  };
  timeSeries: {
    revenue: { name: string; value: number }[];
    customers: { name: string; value: number }[];
    bandwidthUsage: { name: string; upload: number; download: number }[];
  };
  serviceDistribution: { name: string; value: number; color: string }[];
}

interface MetricCardProps {
  title: string;
  value: string;
  change: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  trend?: 'up' | 'down' | 'neutral';
  sparklineData?: { name: string; value: number }[];
}

function MetricCard({
  title,
  value,
  change,
  icon: Icon,
  color,
  trend,
  sparklineData,
}: MetricCardProps) {
  const isPositive = change > 0;
  const trendColor =
    trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600';

  return (
    <div className='bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow'>
      <div className='flex items-center justify-between'>
        <div className={`p-3 rounded-lg bg-${color}-100`}>
          <Icon className={`h-6 w-6 text-${color}-600`} />
        </div>
        {change !== 0 && (
          <div
            className={`flex items-center text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}
          >
            {isPositive ? (
              <ArrowUpIcon className='h-4 w-4 mr-1' />
            ) : (
              <ArrowDownIcon className='h-4 w-4 mr-1' />
            )}
            <span className='font-medium'>{Math.abs(change).toFixed(1)}%</span>
          </div>
        )}
      </div>

      <div className='mt-4'>
        <h3 className='text-sm font-medium text-gray-500'>{title}</h3>
        <p className='mt-1 text-2xl font-bold text-gray-900'>{value}</p>
      </div>

      {sparklineData && (
        <div className='mt-4 h-10'>
          <ResponsiveContainer width='100%' height='100%'>
            <LineChart data={sparklineData}>
              <Line
                type='monotone'
                dataKey='value'
                stroke={`var(--${color}-600)`}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export function DashboardMetrics({ metrics }: { metrics: MetricsData }) {
  const [isRealTime, setIsRealTime] = useState(false);

  const mainMetrics = [
    {
      title: 'Total Customers',
      value: metrics.totalCustomers.toLocaleString(),
      change: metrics.growth.customers,
      icon: UsersIcon,
      color: 'blue',
      trend: 'up' as const,
      sparklineData: metrics.timeSeries.customers.slice(-7),
    },
    {
      title: 'Active Services',
      value: metrics.activeServices.toLocaleString(),
      change: metrics.growth.services,
      icon: WifiIcon,
      color: 'green',
      trend: 'up' as const,
    },
    {
      title: 'Monthly Revenue',
      value: `$${metrics.monthlyRevenue.toLocaleString()}`,
      change: metrics.growth.revenue,
      icon: DollarSignIcon,
      color: 'indigo',
      trend: 'up' as const,
      sparklineData: metrics.timeSeries.revenue.slice(-7),
    },
    {
      title: 'Open Tickets',
      value: metrics.ticketsOpen.toString(),
      change: metrics.growth.tickets,
      icon: TicketIcon,
      color: 'yellow',
      trend: metrics.ticketsOpen > 20 ? 'down' : ('neutral' as const),
    },
  ];

  const secondaryMetrics = [
    {
      title: 'Network Health',
      value: `${metrics.networkHealth}%`,
      change: 0,
      icon: ServerIcon,
      color: 'emerald',
      trend: 'up' as const,
    },
    {
      title: 'Bandwidth Usage',
      value: `${metrics.bandwidthUsage}%`,
      change: 2.3,
      icon: Activity,
      color: 'orange',
      trend: 'neutral' as const,
    },
    {
      title: 'Revenue Growth',
      value: `${metrics.revenueGrowth}%`,
      change: metrics.revenueGrowth,
      icon: TrendingUpIcon,
      color: 'purple',
      trend: 'up' as const,
    },
    {
      title: 'Customer Satisfaction',
      value: `${metrics.customerSatisfaction}%`,
      change: 1.2,
      icon: AlertTriangleIcon,
      color: 'pink',
      trend: 'up' as const,
    },
  ];

  return (
    <div className='space-y-8'>
      {/* Real-time Toggle */}
      <div className='flex justify-between items-center'>
        <div>
          <h2 className='text-lg font-semibold text-gray-900'>Key Metrics</h2>
          <p className='text-sm text-gray-600'>Real-time overview of your ISP operations</p>
        </div>
        <button
          onClick={() => setIsRealTime(!isRealTime)}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            isRealTime
              ? 'bg-green-100 text-green-800 border border-green-200'
              : 'bg-gray-100 text-gray-800 border border-gray-200'
          }`}
        >
          {isRealTime ? '🟢 Real-time' : '⏸️ Static'}
        </button>
      </div>

      {/* Primary Metrics */}
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
        {mainMetrics.map((metric) => (
          <MetricCard key={metric.title} {...metric} />
        ))}
      </div>

      {/* Secondary Metrics */}
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
        {secondaryMetrics.map((metric) => (
          <MetricCard key={metric.title} {...metric} />
        ))}
      </div>

      {/* Charts Section */}
      <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
        {/* Revenue Trend Chart */}
        <div className='lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6'>
          <div className='flex justify-between items-center mb-4'>
            <h3 className='text-lg font-semibold text-gray-900'>Revenue Trend</h3>
            <select className='text-sm border border-gray-300 rounded px-2 py-1'>
              <option>Last 30 days</option>
              <option>Last 90 days</option>
              <option>Last year</option>
            </select>
          </div>
          <ResponsiveContainer width='100%' height={200}>
            <AreaChart data={metrics.timeSeries.revenue}>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis dataKey='name' />
              <YAxis />
              <Tooltip
                formatter={(value: number) => [`$${value.toLocaleString()}`, 'Revenue']}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Area
                type='monotone'
                dataKey='value'
                stroke='#4F46E5'
                fill='#4F46E5'
                fillOpacity={0.1}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Service Distribution Chart */}
        <div className='bg-white rounded-xl shadow-sm border border-gray-200 p-6'>
          <h3 className='text-lg font-semibold text-gray-900 mb-4'>Service Distribution</h3>
          <ResponsiveContainer width='100%' height={200}>
            <PieChart>
              <Pie
                data={metrics.serviceDistribution}
                cx='50%'
                cy='50%'
                innerRadius={40}
                outerRadius={80}
                paddingAngle={5}
                dataKey='value'
              >
                {metrics.serviceDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => [`${value}%`, 'Share']} />
            </PieChart>
          </ResponsiveContainer>
          <div className='mt-4 space-y-2'>
            {metrics.serviceDistribution.map((item) => (
              <div key={item.name} className='flex items-center justify-between text-sm'>
                <div className='flex items-center'>
                  <div
                    className='w-3 h-3 rounded-full mr-2'
                    style={{ backgroundColor: item.color }}
                  />
                  <span className='text-gray-600'>{item.name}</span>
                </div>
                <span className='font-medium text-gray-900'>{item.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bandwidth Usage Chart */}
      <div className='bg-white rounded-xl shadow-sm border border-gray-200 p-6'>
        <h3 className='text-lg font-semibold text-gray-900 mb-4'>Bandwidth Usage (24h)</h3>
        <ResponsiveContainer width='100%' height={300}>
          <BarChart data={metrics.timeSeries.bandwidthUsage}>
            <CartesianGrid strokeDasharray='3 3' />
            <XAxis dataKey='name' />
            <YAxis />
            <Tooltip
              formatter={(value: number, name: string) => [
                `${value} Gbps`,
                name === 'upload' ? 'Upload' : 'Download',
              ]}
            />
            <Bar dataKey='download' fill='#10B981' name='download' />
            <Bar dataKey='upload' fill='#3B82F6' name='upload' />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
