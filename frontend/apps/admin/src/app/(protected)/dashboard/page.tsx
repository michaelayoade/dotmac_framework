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
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
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
    <div className="space-y-6">
      <DashboardMetrics metrics={metrics} />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentActivity activity={activity} />
        <SystemStatus status={status} />
      </div>
    </div>
  );
}

// Mock data fetchers - replace with actual API calls
async function fetchDashboardMetrics() {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 100));
  
  return {
    totalCustomers: 1234,
    activeServices: 1180,
    monthlyRevenue: 58420,
    ticketsOpen: 23,
    growth: {
      customers: 5.2,
      revenue: 8.1,
      services: 3.4,
    },
  };
}

async function fetchRecentActivity() {
  await new Promise(resolve => setTimeout(resolve, 150));
  
  return [
    { id: '1', type: 'customer_added', message: 'New customer John Doe registered', time: '5 minutes ago' },
    { id: '2', type: 'payment_received', message: 'Payment received from Acme Corp', time: '12 minutes ago' },
    { id: '3', type: 'service_activated', message: 'Premium plan activated for Jane Smith', time: '1 hour ago' },
    { id: '4', type: 'ticket_resolved', message: 'Support ticket #1234 resolved', time: '2 hours ago' },
    { id: '5', type: 'network_alert', message: 'Node XYZ-123 back online', time: '3 hours ago' },
  ];
}

async function fetchSystemStatus() {
  await new Promise(resolve => setTimeout(resolve, 200));
  
  return {
    api: 'operational',
    database: 'operational',
    cache: 'operational',
    network: 'degraded',
    billing: 'operational',
    support: 'operational',
  };
}