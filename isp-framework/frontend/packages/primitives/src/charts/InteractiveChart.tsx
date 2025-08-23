/**
 * Interactive Chart Components for ISP Management Platform
 * Enhanced data visualizations with hover states, tooltips, and animations
 */

'use client';

import { useState } from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

// ISP-themed color palette
const COLORS = {
  primary: '#3B82F6',
  secondary: '#10B981',
  accent: '#8B5CF6',
  warning: '#F59E0B',
  danger: '#EF4444',
  success: '#22C55E',
  gradient: {
    primary: 'url(#primaryGradient)',
    secondary: 'url(#secondaryGradient)',
    accent: 'url(#accentGradient)',
  },
};

// Chart gradients
const ChartGradients = () => (
  <defs>
    <linearGradient id='primaryGradient' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='5%' stopColor={COLORS.primary} stopOpacity={0.8} />
      <stop offset='95%' stopColor={COLORS.primary} stopOpacity={0.1} />
    </linearGradient>
    <linearGradient id='secondaryGradient' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='5%' stopColor={COLORS.secondary} stopOpacity={0.8} />
      <stop offset='95%' stopColor={COLORS.secondary} stopOpacity={0.1} />
    </linearGradient>
    <linearGradient id='accentGradient' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='5%' stopColor={COLORS.accent} stopOpacity={0.8} />
      <stop offset='95%' stopColor={COLORS.accent} stopOpacity={0.1} />
    </linearGradient>
  </defs>
);

// Custom tooltip component
interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
  formatter?: (value: any, name: string) => [string, string];
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label, formatter }) => {
  if (active && payload && payload.length) {
    return (
      <div className='bg-white border border-gray-200 rounded-lg shadow-lg p-3 backdrop-blur-sm'>
        <p className='text-sm font-semibold text-gray-900 mb-2'>{label}</p>
        {payload.map((entry, index) => (
          <div key={index} className='flex items-center space-x-2 mb-1'>
            <div className='w-3 h-3 rounded-full' style={{ backgroundColor: entry.color }} />
            <span className='text-sm text-gray-600'>
              {formatter ? formatter(entry.value, entry.name)[1] : entry.name}:
            </span>
            <span className='text-sm font-semibold text-gray-900'>
              {formatter ? formatter(entry.value, entry.name)[0] : entry.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

// Revenue Trends Area Chart
interface RevenueData {
  month: string;
  revenue: number;
  target: number;
  previousYear: number;
}

interface RevenueChartProps {
  data: RevenueData[];
  height?: number;
}

export const RevenueChart: React.FC<RevenueChartProps> = ({ data, height = 300 }) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  return (
    <div className='w-full' style={{ height }}>
      <ResponsiveContainer width='100%' height='100%'>
        <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <ChartGradients />
          <CartesianGrid strokeDasharray='3 3' stroke='#E5E7EB' />
          <XAxis
            dataKey='month'
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#6B7280' }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#6B7280' }}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
          />
          <Tooltip
            content={
              <CustomTooltip formatter={(value, name) => [`$${value.toLocaleString()}`, name]} />
            }
          />
          <Legend />
          <Area
            type='monotone'
            dataKey='revenue'
            stroke={COLORS.primary}
            strokeWidth={2}
            fill={COLORS.gradient.primary}
            name='Current Revenue'
            onMouseEnter={(_, index) => setActiveIndex(index)}
            onMouseLeave={() => setActiveIndex(null)}
          />
          <Area
            type='monotone'
            dataKey='previousYear'
            stroke={COLORS.secondary}
            strokeWidth={2}
            fill={COLORS.gradient.secondary}
            name='Previous Year'
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

// Network Usage Bar Chart
interface NetworkUsageData {
  hour: string;
  download: number;
  upload: number;
  peak: number;
}

interface NetworkUsageChartProps {
  data: NetworkUsageData[];
  height?: number;
}

export const NetworkUsageChart: React.FC<NetworkUsageChartProps> = ({ data, height = 250 }) => {
  return (
    <div className='w-full' style={{ height }}>
      <ResponsiveContainer width='100%' height='100%'>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray='3 3' stroke='#E5E7EB' />
          <XAxis
            dataKey='hour'
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#6B7280' }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#6B7280' }}
            tickFormatter={(value) => `${value}GB`}
          />
          <Tooltip content={<CustomTooltip formatter={(value, name) => [`${value}GB`, name]} />} />
          <Legend />
          <Bar dataKey='download' fill={COLORS.primary} name='Download' radius={[2, 2, 0, 0]} />
          <Bar dataKey='upload' fill={COLORS.secondary} name='Upload' radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// Service Status Pie Chart
interface ServiceStatusData {
  name: string;
  value: number;
  status: 'online' | 'maintenance' | 'offline';
}

interface ServiceStatusChartProps {
  data: ServiceStatusData[];
  height?: number;
}

export const ServiceStatusChart: React.FC<ServiceStatusChartProps> = ({ data, height = 250 }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return COLORS.success;
      case 'maintenance':
        return COLORS.warning;
      case 'offline':
        return COLORS.danger;
      default:
        return COLORS.primary;
    }
  };

  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  return (
    <div className='w-full' style={{ height }}>
      <ResponsiveContainer width='100%' height='100%'>
        <PieChart>
          <Pie
            data={data}
            cx='50%'
            cy='50%'
            outerRadius={80}
            innerRadius={40}
            paddingAngle={2}
            dataKey='value'
            onMouseEnter={(_, index) => setActiveIndex(index)}
            onMouseLeave={() => setActiveIndex(null)}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={getStatusColor(entry.status)}
                stroke={index === activeIndex ? '#FFF' : 'none'}
                strokeWidth={index === activeIndex ? 2 : 0}
              />
            ))}
          </Pie>
          <Tooltip
            content={<CustomTooltip formatter={(value, name) => [`${value} services`, name]} />}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

// Bandwidth Utilization Line Chart
interface BandwidthData {
  time: string;
  utilization: number;
  capacity: number;
}

interface BandwidthChartProps {
  data: BandwidthData[];
  height?: number;
}

export const BandwidthChart: React.FC<BandwidthChartProps> = ({ data, height = 200 }) => {
  return (
    <div className='w-full' style={{ height }}>
      <ResponsiveContainer width='100%' height='100%'>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray='3 3' stroke='#E5E7EB' />
          <XAxis
            dataKey='time'
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#6B7280' }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#6B7280' }}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip content={<CustomTooltip formatter={(value, name) => [`${value}%`, name]} />} />
          <Legend />
          <Line
            type='monotone'
            dataKey='utilization'
            stroke={COLORS.primary}
            strokeWidth={3}
            dot={{ fill: COLORS.primary, strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: COLORS.primary, strokeWidth: 2, fill: '#FFF' }}
            name='Bandwidth Utilization'
          />
          <Line
            type='monotone'
            dataKey='capacity'
            stroke={COLORS.danger}
            strokeWidth={2}
            strokeDasharray='5 5'
            dot={false}
            name='Capacity Limit'
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
