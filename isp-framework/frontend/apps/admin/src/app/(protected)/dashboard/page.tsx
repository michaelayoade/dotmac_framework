import { Suspense } from 'react';
import { AdminLayout } from '../../../components/layout/AdminLayout';
import { SkeletonDashboard } from '@dotmac/primitives';
import { DashboardMetrics } from '../../../components/dashboard/DashboardMetrics';
import { RecentActivity } from '../../../components/dashboard/RecentActivity';
import { SystemStatus } from '../../../components/dashboard/SystemStatus';

// Server Component
export default function DashboardPage() {
  return (
    <AdminLayout>
      <div className='space-y-6'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Dashboard</h1>
          <p className='mt-1 text-sm text-gray-500'>
            Monitor your ISP operations and system health
          </p>
        </div>

        <Suspense fallback={<SkeletonDashboard />}>
          <DashboardContent />
        </Suspense>
      </div>
    </AdminLayout>
  );
}

async function DashboardContent() {
  // These would be actual API calls in production
  const [metrics, activity, status] = await Promise.all([
    fetchDashboardMetrics(),
    fetchRecentActivity(),
    fetchSystemStatus(),
  ]);

  return (
    <div className='space-y-6'>
      <DashboardMetrics metrics={metrics} />

      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        <RecentActivity activity={activity} />
        <SystemStatus status={status} />
      </div>
    </div>
  );
}

// Mock data fetchers - replace with actual API calls
async function fetchDashboardMetrics() {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 100));

  return {
    totalCustomers: 15234,
    activeServices: 18567,
    monthlyRevenue: 1850000,
    ticketsOpen: 23,
    networkHealth: 99.2,
    bandwidthUsage: 78.5,
    revenueGrowth: 12.4,
    customerSatisfaction: 94.7,
    newInstallations: 187, // This month
    churnRate: 2.3, // Monthly percentage
    averageArpu: 98.75, // Average Revenue Per User
    fiberPenetration: 78.5, // Percentage of fiber customers
    growth: {
      customers: 8.2,
      revenue: 12.4,
      services: 5.7,
      tickets: -15.3,
      fiber: 15.8, // Fiber customer growth
      arpu: 3.2, // ARPU growth
    },
    timeSeries: {
      revenue: [
        { name: 'Jan', value: 1650000, fiber: 1320000, cable: 280000, business: 50000 },
        { name: 'Feb', value: 1720000, fiber: 1392000, cable: 278000, business: 50000 },
        { name: 'Mar', value: 1680000, fiber: 1360000, cable: 270000, business: 50000 },
        { name: 'Apr', value: 1750000, fiber: 1435000, cable: 265000, business: 50000 },
        { name: 'May', value: 1820000, fiber: 1510000, cable: 260000, business: 50000 },
        { name: 'Jun', value: 1850000, fiber: 1540000, cable: 260000, business: 50000 },
      ],
      customers: [
        { name: 'Jan', value: 14200, residential: 12680, business: 890, bulk: 630 },
        { name: 'Feb', value: 14450, residential: 12890, business: 920, bulk: 640 },
        { name: 'Mar', value: 14680, residential: 13080, business: 945, bulk: 655 },
        { name: 'Apr', value: 14890, residential: 13260, business: 970, bulk: 660 },
        { name: 'May', value: 15100, residential: 13450, business: 985, bulk: 665 },
        { name: 'Jun', value: 15234, residential: 13569, business: 995, bulk: 670 },
      ],
      bandwidthUsage: [
        { name: '00:00', upload: 1.2, download: 4.8, peak_hour: false },
        { name: '04:00', upload: 2.1, download: 8.5, peak_hour: false },
        { name: '08:00', upload: 4.2, download: 12.3, peak_hour: true },
        { name: '12:00', upload: 5.8, download: 15.7, peak_hour: true },
        { name: '16:00', upload: 6.2, download: 18.4, peak_hour: false },
        { name: '20:00', upload: 7.1, download: 21.2, peak_hour: true },
        { name: '23:59', upload: 5.4, download: 16.8, peak_hour: false },
      ],
      networkHealth: [
        { name: 'Week 1', uptime: 99.95, incidents: 1, mttr: 15 },
        { name: 'Week 2', uptime: 99.89, incidents: 2, mttr: 22 },
        { name: 'Week 3', uptime: 99.97, incidents: 1, mttr: 8 },
        { name: 'Week 4', uptime: 99.93, incidents: 1, mttr: 12 },
      ],
    },
    serviceDistribution: [
      { name: 'DotMac Fiber 100/100', value: 35, color: '#3B82F6', customers: 5332, arpu: 79.99 },
      { name: 'DotMac Fiber 500/500', value: 25, color: '#10B981', customers: 3809, arpu: 149.99 },
      { name: 'DotMac Fiber 1Gbps', value: 18, color: '#8B5CF6', customers: 2742, arpu: 199.99 },
      { name: 'Business Pro 500/500', value: 12, color: '#F59E0B', customers: 1828, arpu: 299.99 },
      { name: 'Enterprise Dedicated', value: 5, color: '#EF4444', customers: 762, arpu: 1499.99 },
      { name: 'Essential Cable 50/10', value: 3, color: '#6B7280', customers: 457, arpu: 49.99 },
      { name: 'Bulk/MDU Services', value: 2, color: '#F97316', customers: 304, arpu: 45.83 },
    ],
    territories: [
      { name: 'Seattle Central', customers: 4250, fiber_ready: 98, penetration: 82 },
      { name: 'Eastside', customers: 3890, fiber_ready: 95, penetration: 75 },
      { name: 'North Seattle', customers: 2980, fiber_ready: 90, penetration: 68 },
      { name: 'Downtown', customers: 2120, fiber_ready: 100, penetration: 95 },
      { name: 'South King County', customers: 1994, fiber_ready: 85, penetration: 62 },
    ],
    networkNodes: [
      { id: 'SEA-CORE-01', status: 'operational', utilization: 67, capacity: '100Gbps' },
      { id: 'BEL-DIST-02', status: 'operational', utilization: 82, capacity: '40Gbps' },
      { id: 'RED-DIST-03', status: 'maintenance', utilization: 0, capacity: '40Gbps' },
      { id: 'KIR-DIST-04', status: 'operational', utilization: 55, capacity: '40Gbps' },
    ],
  };
}

async function fetchRecentActivity() {
  await new Promise((resolve) => setTimeout(resolve, 150));

  return [
    {
      id: '1',
      type: 'fiber_installation',
      message: 'Fiber installation completed for Sarah Wilson (456 Pine Ave)',
      time: '5 minutes ago',
      priority: 'normal',
    },
    {
      id: '2',
      type: 'payment_received',
      message: 'Auto-payment processed: Green Valley Apartments - $2,724.99',
      time: '12 minutes ago',
      priority: 'normal',
    },
    {
      id: '3',
      type: 'service_upgrade',
      message: 'TechCorp Solutions upgraded to Business Pro 1Gbps',
      time: '25 minutes ago',
      priority: 'normal',
    },
    {
      id: '4',
      type: 'network_maintenance',
      message: 'Scheduled maintenance completed on RED-DIST-03 node',
      time: '1 hour ago',
      priority: 'high',
    },
    {
      id: '5',
      type: 'ticket_resolved',
      message: 'Speed optimization ticket resolved for CUST-2847 (Eastside)',
      time: '2 hours ago',
      priority: 'normal',
    },
    {
      id: '6',
      type: 'new_territory',
      message: 'South King County territory expanded - 47 new addresses',
      time: '3 hours ago',
      priority: 'high',
    },
    {
      id: '7',
      type: 'bgp_peering',
      message: 'New BGP peering established with Tier-1 provider',
      time: '4 hours ago',
      priority: 'critical',
    },
    {
      id: '8',
      type: 'bulk_signup',
      message: 'Marina Towers (96 units) signed bulk service agreement',
      time: '6 hours ago',
      priority: 'high',
    },
  ];
}

async function fetchSystemStatus() {
  await new Promise((resolve) => setTimeout(resolve, 200));

  return {
    core_network: 'operational',
    fiber_infrastructure: 'operational',
    bgp_routing: 'operational',
    dhcp_dns: 'operational',
    billing_system: 'operational',
    customer_portal: 'operational',
    noc_monitoring: 'operational',
    provisioning: 'maintenance',
    field_management: 'operational',
    peering_connections: 'degraded',
  };
}
