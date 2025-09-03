'use client';

import { useCachedData } from '@dotmac/headless';
import { Card } from '@dotmac/ui/customer';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Wifi,
  Zap,
} from 'lucide-react';
import { useState } from 'react';

// Mock usage analytics data
const mockUsageData = {
  currentPeriod: {
    startDate: '2024-01-15',
    endDate: '2024-02-14',
    daysRemaining: 17,
    progressPercent: 43,
  },
  dataUsage: {
    current: 450,
    limit: 1000,
    unit: 'GB',
    percentUsed: 45,
    dailyAverage: 15.2,
    trend: 'up',
    trendPercent: 12,
  },
  speedTests: [
    {
      id: 'ST-001',
      timestamp: '2024-01-29T14:30:00Z',
      downloadSpeed: 98.5,
      uploadSpeed: 97.2,
      ping: 12,
      jitter: 2.1,
      status: 'good',
    },
    {
      id: 'ST-002',
      timestamp: '2024-01-28T10:15:00Z',
      downloadSpeed: 102.1,
      uploadSpeed: 99.8,
      ping: 11,
      jitter: 1.8,
      status: 'excellent',
    },
    {
      id: 'ST-003',
      timestamp: '2024-01-27T16:45:00Z',
      downloadSpeed: 94.2,
      uploadSpeed: 95.1,
      ping: 15,
      jitter: 3.2,
      status: 'good',
    },
  ],
  dailyUsage: [
    { date: '2024-01-23', usage: 18.5, peak: 22.1 },
    { date: '2024-01-24', usage: 14.2, peak: 16.8 },
    { date: '2024-01-25', usage: 21.7, peak: 25.3 },
    { date: '2024-01-26', usage: 16.3, peak: 19.7 },
    { date: '2024-01-27', usage: 19.8, peak: 23.4 },
    { date: '2024-01-28', usage: 13.1, peak: 15.9 },
    { date: '2024-01-29', usage: 22.4, peak: 26.8 },
  ],
  networkStatus: {
    status: 'operational',
    uptime: 99.97,
    lastOutage: '2024-01-20T03:15:00Z',
    maintenanceScheduled: null,
  },
  deviceConnections: {
    total: 12,
    active: 8,
    devices: [
      { name: 'iPhone 14 Pro', type: 'mobile', status: 'active', usage: 45.2 },
      { name: 'MacBook Pro', type: 'computer', status: 'active', usage: 128.7 },
      { name: 'Smart TV', type: 'streaming', status: 'active', usage: 89.3 },
      { name: 'iPad Air', type: 'tablet', status: 'inactive', usage: 12.1 },
      { name: 'Smart Thermostat', type: 'iot', status: 'active', usage: 0.8 },
    ],
  },
};

export function UsageAnalytics() {
  const [selectedPeriod, setSelectedPeriod] = useState<'7d' | '30d' | '90d'>('30d');
  const [runningSpeedTest, setRunningSpeedTest] = useState(false);

  const { data: usageData, isLoading } = useCachedData(
    `customer-usage-${selectedPeriod}`,
    async () => mockUsageData,
    { ttl: 2 * 60 * 1000 }
  );

  const getSpeedStatus = (speed: number, expected: number) => {
    const percentage = (speed / expected) * 100;
    if (percentage >= 90) {
      return { status: 'excellent', color: 'text-green-600' };
    }
    if (percentage >= 75) {
      return { status: 'good', color: 'text-blue-600' };
    }
    if (percentage >= 50) {
      return { status: 'fair', color: 'text-yellow-600' };
    }
    return { status: 'poor', color: 'text-red-600' };
  };

  const getDeviceIcon = (type: string) => {
    switch (type) {
      case 'mobile':
        return '📱';
      case 'computer':
        return '💻';
      case 'streaming':
        return '📺';
      case 'tablet':
        return '⏯️';
      case 'iot':
        return '🏠';
      default:
        return '📱';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const runSpeedTest = async () => {
    setRunningSpeedTest(true);
    // Simulate speed test
    await new Promise((resolve) => setTimeout(resolve, 3000));
    setRunningSpeedTest(false);
    // In real app, this would refresh the speed test data
  };

  if (isLoading || !usageData) {
    return (
      <div className='flex h-64 items-center justify-center'>
        <div className='h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2' />
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <h1 className='font-bold text-2xl text-gray-900'>Usage & Performance</h1>
        <div className='flex items-center space-x-3'>
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value as '7d' | '30d' | '90d')}
            className='rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
          >
            <option value='7d'>Last 7 days</option>
            <option value='30d'>Last 30 days</option>
            <option value='90d'>Last 90 days</option>
          </select>
          <button
            type='button'
            onClick={runSpeedTest}
            onKeyDown={(e) => e.key === 'Enter' && runSpeedTest}
            disabled={runningSpeedTest}
            className={`flex items-center rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 ${
              runningSpeedTest ? 'cursor-not-allowed opacity-50' : ''
            }`}
          >
            <Zap className={`mr-2 h-4 w-4 ${runningSpeedTest ? 'animate-pulse' : ''}`} />
            {runningSpeedTest ? 'Running Test...' : 'Speed Test'}
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className='grid grid-cols-1 gap-6 md:grid-cols-4'>
        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Data Usage</p>
              <p className='font-bold text-2xl text-gray-900'>
                {usageData.dataUsage.current} {usageData.dataUsage.unit}
              </p>
              <p className='text-gray-500 text-sm'>
                of {usageData.dataUsage.limit} {usageData.dataUsage.unit}
              </p>
            </div>
            <div
              className={`flex items-center ${
                usageData.dataUsage.trend === 'up' ? 'text-yellow-600' : 'text-green-600'
              }`}
            >
              {usageData.dataUsage.trend === 'up' ? (
                <TrendingUp className='h-5 w-5' />
              ) : (
                <TrendingDown className='h-5 w-5' />
              )}
            </div>
          </div>
          <div className='mt-4'>
            <div className='h-2 w-full rounded-full bg-gray-200'>
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  usageData.dataUsage.percentUsed > 80
                    ? 'bg-red-500'
                    : usageData.dataUsage.percentUsed > 60
                      ? 'bg-yellow-500'
                      : 'bg-blue-600'
                }`}
                style={{ width: `${Math.min(usageData.dataUsage.percentUsed, 100)}%` }}
              />
            </div>
            <p className='mt-1 text-gray-500 text-xs'>
              {usageData.dataUsage.percentUsed}% used • {usageData.currentPeriod.daysRemaining} days
              remaining
            </p>
          </div>
        </Card>

        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Daily Average</p>
              <p className='font-bold text-2xl text-gray-900'>
                {usageData.dataUsage.dailyAverage} GB
              </p>
              <p
                className={`text-sm ${
                  usageData.dataUsage.trend === 'up' ? 'text-yellow-600' : 'text-green-600'
                }`}
              >
                {usageData.dataUsage.trend === 'up' ? '+' : '-'}
                {usageData.dataUsage.trendPercent}% vs last period
              </p>
            </div>
            <Activity className='h-8 w-8 text-blue-600' />
          </div>
        </Card>

        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Network Uptime</p>
              <p className='font-bold text-2xl text-gray-900'>{usageData.networkStatus.uptime}%</p>
              <p className='text-green-600 text-sm'>Excellent</p>
            </div>
            <CheckCircle className='h-8 w-8 text-green-600' />
          </div>
        </Card>

        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Connected Devices</p>
              <p className='font-bold text-2xl text-gray-900'>
                {usageData.deviceConnections.active}
              </p>
              <p className='text-gray-500 text-sm'>of {usageData.deviceConnections.total} total</p>
            </div>
            <Wifi className='h-8 w-8 text-purple-600' />
          </div>
        </Card>
      </div>

      <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
        {/* Speed Test Results */}
        <Card className='p-6'>
          <div className='mb-4 flex items-center justify-between'>
            <h3 className='font-semibold text-gray-900 text-lg'>Recent Speed Tests</h3>
            <button
              type='button'
              onClick={runSpeedTest}
              onKeyDown={(e) => e.key === 'Enter' && runSpeedTest}
              disabled={runningSpeedTest}
              className='flex items-center font-medium text-blue-600 text-sm hover:text-blue-800'
            >
              <RefreshCw className={`mr-1 h-4 w-4 ${runningSpeedTest ? 'animate-spin' : ''}`} />
              {runningSpeedTest ? 'Testing...' : 'Run Test'}
            </button>
          </div>

          <div className='space-y-4'>
            {usageData.speedTests.map((test, index) => {
              const downloadStatus = getSpeedStatus(test.downloadSpeed, 100);
              const uploadStatus = getSpeedStatus(test.uploadSpeed, 100);

              return (
                <div
                  key={test.id}
                  className={`rounded-lg border p-4 ${
                    index === 0 ? 'border-blue-200 bg-blue-50' : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className='mb-2 flex items-start justify-between'>
                    <span className='text-gray-600 text-sm'>{formatTimestamp(test.timestamp)}</span>
                    <span
                      className={`rounded-full px-2 py-1 font-medium text-xs ${
                        test.status === 'excellent'
                          ? 'bg-green-100 text-green-800'
                          : test.status === 'good'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {test.status.toUpperCase()}
                    </span>
                  </div>

                  <div className='grid grid-cols-2 gap-4 text-sm'>
                    <div>
                      <span className='text-gray-600'>Download:</span>
                      <span className={`ml-2 font-medium ${downloadStatus.color}`}>
                        {test.downloadSpeed} Mbps
                      </span>
                    </div>
                    <div>
                      <span className='text-gray-600'>Upload:</span>
                      <span className={`ml-2 font-medium ${uploadStatus.color}`}>
                        {test.uploadSpeed} Mbps
                      </span>
                    </div>
                    <div>
                      <span className='text-gray-600'>Ping:</span>
                      <span className='ml-2 font-medium'>{test.ping} ms</span>
                    </div>
                    <div>
                      <span className='text-gray-600'>Jitter:</span>
                      <span className='ml-2 font-medium'>{test.jitter} ms</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Daily Usage Chart */}
        <Card className='p-6'>
          <h3 className='mb-4 font-semibold text-gray-900 text-lg'>Daily Usage Trend</h3>

          <div className='space-y-2'>
            {usageData.dailyUsage.map((day, _index) => {
              const maxUsage = Math.max(...usageData.dailyUsage.map((d) => d.peak));
              const usagePercent = (day.usage / maxUsage) * 100;
              const peakPercent = (day.peak / maxUsage) * 100;

              return (
                <div key={day.date} className='flex items-center'>
                  <div className='mr-3 w-16 text-right text-gray-600 text-xs'>
                    {formatDate(day.date)}
                  </div>
                  <div className='relative h-6 flex-1 rounded bg-gray-100'>
                    <div
                      className='absolute top-0 left-0 h-full rounded bg-blue-200'
                      style={{ width: `${peakPercent}%` }}
                    />
                    <div
                      className='absolute top-0 left-0 h-full rounded bg-blue-600'
                      style={{ width: `${usagePercent}%` }}
                    />
                  </div>
                  <div className='ml-3 w-16 text-right text-gray-900 text-xs'>{day.usage} GB</div>
                </div>
              );
            })}
          </div>

          <div className='mt-4 flex items-center justify-between text-gray-600 text-xs'>
            <div className='flex items-center'>
              <div className='mr-2 h-3 w-3 rounded bg-blue-600' />
              <span>Usage</span>
            </div>
            <div className='flex items-center'>
              <div className='mr-2 h-3 w-3 rounded bg-blue-200' />
              <span>Peak</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Connected Devices */}
      <Card className='p-6'>
        <h3 className='mb-4 font-semibold text-gray-900 text-lg'>Connected Devices</h3>

        <div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3'>
          {usageData.deviceConnections.devices.map((device, index) => (
            <div
              key={`device-${device.mac || index}`}
              className={`rounded-lg border p-4 ${
                device.status === 'active'
                  ? 'border-green-200 bg-green-50'
                  : 'border-gray-200 bg-gray-50'
              }`}
            >
              <div className='mb-2 flex items-center justify-between'>
                <div className='flex items-center'>
                  <span className='mr-2 text-lg'>{getDeviceIcon(device.type)}</span>
                  <span className='font-medium text-gray-900'>{device.name}</span>
                </div>
                <div
                  className={`h-3 w-3 rounded-full ${
                    device.status === 'active' ? 'bg-green-500' : 'bg-gray-400'
                  }`}
                />
              </div>

              <div className='text-gray-600 text-sm'>
                <div className='flex justify-between'>
                  <span>Status:</span>
                  <span
                    className={`capitalize ${
                      device.status === 'active' ? 'text-green-600' : 'text-gray-600'
                    }`}
                  >
                    {device.status}
                  </span>
                </div>
                <div className='flex justify-between'>
                  <span>Usage:</span>
                  <span className='font-medium'>{device.usage} GB</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Network Status */}
      <Card className='p-6'>
        <h3 className='mb-4 font-semibold text-gray-900 text-lg'>Network Status</h3>

        <div className='flex items-center justify-between'>
          <div className='flex items-center'>
            <div
              className={`mr-3 h-4 w-4 rounded-full ${
                usageData.networkStatus.status === 'operational' ? 'bg-green-500' : 'bg-yellow-500'
              }`}
            />
            <div>
              <p className='font-medium text-gray-900 capitalize'>
                {usageData.networkStatus.status}
              </p>
              <p className='text-gray-600 text-sm'>
                {usageData.networkStatus.uptime}% uptime • Last outage:{' '}
                {formatTimestamp(usageData.networkStatus.lastOutage)}
              </p>
            </div>
          </div>

          {usageData.networkStatus.maintenanceScheduled ? (
            <div className='flex items-center text-sm text-yellow-600'>
              <AlertTriangle className='mr-1 h-4 w-4' />
              <span>Maintenance scheduled</span>
            </div>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
