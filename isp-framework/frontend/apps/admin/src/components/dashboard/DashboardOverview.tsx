'use client';

import { useOfflineSync, useTenantStore } from '@dotmac/headless';
import { NetworkDeviceWidget, RealTimeMetricsWidget } from '@dotmac/primitives';
import { AdminCard as Card } from '@dotmac/styled-components/admin';
import { AlertTriangle, Database, Network, TrendingUp, Users, Wifi, WifiOff } from 'lucide-react';

// Mock data - in real app this would come from API
const mockMetrics = {
  totalCustomers: 1247,
  activeConnections: 1189,
  networkUptime: 99.8,
  pendingTickets: 23,
  monthlyRevenue: 145750,
  revenueGrowth: 12.5,
};

const mockDevices = [
  {
    id: 'router-001',
    name: 'Core Router 1',
    type: 'router' as const,
    status: 'online' as const,
    location: 'Data Center A',
    uptime: 2547600, // 29.5 days in seconds
    traffic: { inbound: 850, outbound: 720 },
    errors: 0,
  },
  {
    id: 'switch-002',
    name: 'Access Switch 2',
    type: 'switch' as const,
    status: 'warning' as const,
    location: 'Building B',
    uptime: 432000, // 5 days
    traffic: { inbound: 340, outbound: 290 },
    errors: 3,
  },
  {
    id: 'access-point-003',
    name: 'WiFi AP Floor 3',
    type: 'access_point' as const,
    status: 'offline' as const,
    location: 'Office Floor 3',
    uptime: 0,
    traffic: { inbound: 0, outbound: 0 },
    errors: 1,
  },
];

export function DashboardOverview() {
  const { currentTenant: _currentTenant } = useTenantStore();
  const { isOnline, pendingOperations } = useOfflineSync();

  return (
    <div className='space-y-6'>
      {/* Connection Status */}
      {!isOnline && (
        <div className='rounded-lg border border-orange-200 bg-orange-50 p-4'>
          <div className='flex items-center'>
            <WifiOff className='mr-2 h-5 w-5 text-orange-600' />
            <div>
              <h3 className='font-medium text-orange-800'>Working Offline</h3>
              <p className='text-orange-700 text-sm'>
                You're currently offline.{' '}
                {pendingOperations &&
                  pendingOperations > 0 &&
                  `${pendingOperations} operations queued for sync.`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Key Metrics */}
      <div className='grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4'>
        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Total Customers</p>
              <p className='font-bold text-3xl text-gray-900'>
                {mockMetrics.totalCustomers.toLocaleString()}
              </p>
            </div>
            <Users className='h-8 w-8 text-blue-600' />
          </div>
        </Card>

        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Active Connections</p>
              <p className='font-bold text-3xl text-gray-900'>
                {mockMetrics.activeConnections.toLocaleString()}
              </p>
            </div>
            <Wifi className='h-8 w-8 text-green-600' />
          </div>
        </Card>

        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Network Uptime</p>
              <p className='font-bold text-3xl text-gray-900'>{mockMetrics.networkUptime}%</p>
            </div>
            <Network className='h-8 w-8 text-green-600' />
          </div>
        </Card>

        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Open Tickets</p>
              <p className='font-bold text-3xl text-gray-900'>{mockMetrics.pendingTickets}</p>
            </div>
            <AlertTriangle className='h-8 w-8 text-orange-600' />
          </div>
        </Card>
      </div>

      {/* Network Devices Status */}
      <div className='grid grid-cols-1 gap-6 lg:grid-cols-3'>
        {mockDevices.map((device) => (
          <NetworkDeviceWidget key={device.id} device={device} className='h-full' />
        ))}
      </div>

      {/* System Metrics */}
      <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
        <RealTimeMetricsWidget
          title='Server Performance'
          metrics={[
            { label: 'CPU Usage', value: 45, unit: '%', status: 'normal' },
            { label: 'Memory Usage', value: 68, unit: '%', status: 'warning' },
            { label: 'Disk Usage', value: 23, unit: '%', status: 'normal' },
            { label: 'Network I/O', value: 12.5, unit: 'MB/s', status: 'normal' },
          ]}
          refreshInterval={5000}
        />

        <RealTimeMetricsWidget
          title='Database Performance'
          metrics={[
            { label: 'Active Connections', value: 124, unit: '', status: 'normal' },
            { label: 'Query Response', value: 2.3, unit: 'ms', status: 'normal' },
            { label: 'Cache Hit Rate', value: 94, unit: '%', status: 'normal' },
            { label: 'Storage Used', value: 156, unit: 'GB', status: 'normal' },
          ]}
          refreshInterval={10000}
        />
      </div>

      {/* Revenue Overview */}
      <Card className='p-6'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='font-semibold text-gray-900 text-lg'>Revenue Overview</h3>
          <TrendingUp className='h-5 w-5 text-green-600' />
        </div>
        <div className='grid grid-cols-1 gap-6 md:grid-cols-2'>
          <div>
            <p className='font-medium text-gray-600 text-sm'>Monthly Revenue</p>
            <p className='font-bold text-2xl text-gray-900'>
              ${mockMetrics.monthlyRevenue.toLocaleString()}
            </p>
          </div>
          <div>
            <p className='font-medium text-gray-600 text-sm'>Growth Rate</p>
            <p className='font-bold text-2xl text-green-600'>+{mockMetrics.revenueGrowth}%</p>
          </div>
        </div>
      </Card>

      {/* Quick Actions */}
      <Card className='p-6'>
        <h3 className='mb-4 font-semibold text-gray-900 text-lg'>Quick Actions</h3>
        <div className='grid grid-cols-2 gap-4 md:grid-cols-4'>
          <button
            type='button'
            className='rounded-lg border p-4 text-center transition-colors hover:bg-gray-50'
          >
            <Users className='mx-auto mb-2 h-6 w-6 text-gray-600' />
            <span className='font-medium text-sm'>Add Customer</span>
          </button>
          <button
            type='button'
            className='rounded-lg border p-4 text-center transition-colors hover:bg-gray-50'
          >
            <Network className='mx-auto mb-2 h-6 w-6 text-gray-600' />
            <span className='font-medium text-sm'>Network Config</span>
          </button>
          <button
            type='button'
            className='rounded-lg border p-4 text-center transition-colors hover:bg-gray-50'
          >
            <AlertTriangle className='mx-auto mb-2 h-6 w-6 text-gray-600' />
            <span className='font-medium text-sm'>View Alerts</span>
          </button>
          <button
            type='button'
            className='rounded-lg border p-4 text-center transition-colors hover:bg-gray-50'
          >
            <Database className='mx-auto mb-2 h-6 w-6 text-gray-600' />
            <span className='font-medium text-sm'>System Backup</span>
          </button>
        </div>
      </Card>
    </div>
  );
}
