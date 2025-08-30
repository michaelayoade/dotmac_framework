'use client';

import { UniversalDashboard, UniversalMetricCard, UniversalKPISection } from '@dotmac/primitives';
import { UniversalChart } from '@dotmac/primitives';
import { UniversalDataTable } from '@dotmac/primitives';
import { Button } from '@dotmac/primitives';
import { useAuth } from '@dotmac/auth';
import { useState, useEffect } from 'react';

// Sample data - replace with real API calls
const sampleMetrics = [
  {
    id: 'active-resellers',
    title: 'Active Resellers',
    value: 247,
    trend: { direction: 'up' as const, percentage: 12 },
    icon: 'Users'
  },
  {
    id: 'monthly-revenue',
    title: 'Monthly Revenue',
    value: '$2.4M',
    trend: { direction: 'up' as const, percentage: 18 },
    icon: 'DollarSign'
  },
  {
    id: 'pending-commissions',
    title: 'Pending Commissions',
    value: '$124K',
    trend: { direction: 'down' as const, percentage: 5 },
    icon: 'CreditCard'
  },
  {
    id: 'new-partners',
    title: 'New Partners',
    value: 23,
    trend: { direction: 'up' as const, percentage: 8 },
    icon: 'UserPlus'
  }
];

const sampleChartData = [
  { name: 'Jan', revenue: 180000, commissions: 18000 },
  { name: 'Feb', revenue: 210000, commissions: 21000 },
  { name: 'Mar', revenue: 195000, commissions: 19500 },
  { name: 'Apr', revenue: 240000, commissions: 24000 },
  { name: 'May', revenue: 260000, commissions: 26000 },
  { name: 'Jun', revenue: 280000, commissions: 28000 }
];

const sampleTableData = [
  { id: 1, partner: 'TechNet Solutions', status: 'Active', revenue: '$45K', commission: '$4.5K', region: 'West' },
  { id: 2, partner: 'ConnectCorp', status: 'Active', revenue: '$38K', commission: '$3.8K', region: 'East' },
  { id: 3, partner: 'NetWorks Inc', status: 'Pending', revenue: '$52K', commission: '$5.2K', region: 'Central' },
  { id: 4, partner: 'ISP Partners', status: 'Active', revenue: '$29K', commission: '$2.9K', region: 'South' },
  { id: 5, partner: 'Digital Bridge', status: 'Review', revenue: '$67K', commission: '$6.7K', region: 'North' }
];

const tableColumns = [
  { key: 'partner', label: 'Partner', sortable: true },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'revenue', label: 'Revenue', sortable: true, format: 'currency' as const },
  { key: 'commission', label: 'Commission', sortable: true, format: 'currency' as const },
  { key: 'region', label: 'Region', sortable: true }
];

export function IntegratedDashboard() {
  const { user } = useAuth();
  const [refreshing, setRefreshing] = useState(false);

  // Simulate data refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setRefreshing(false);
  };

  const dashboardActions = [
    {
      id: 'refresh-data',
      label: 'Refresh Data',
      variant: 'secondary' as const,
      onClick: handleRefresh
    },
    {
      id: 'export-report',
      label: 'Export Report',
      variant: 'primary' as const,
      onClick: () => console.log('Export report')
    }
  ];

  return (
    <UniversalDashboard
      variant="management"
      title="Management Dashboard"
      subtitle={`Welcome back, ${user?.name || 'User'}`}
      user={user}
      tenant={{ id: 'management', name: 'Management Portal' }}
      actions={dashboardActions}
      isLoading={refreshing}
      onRefresh={handleRefresh}
      spacing="relaxed"
      maxWidth="7xl"
    >
      {/* KPI Section */}
      <UniversalKPISection
        title="Key Performance Indicators"
        subtitle="Performance metrics overview"
        kpis={sampleMetrics}
        columns={4}
        gap="normal"
      />

      {/* Revenue Chart */}
      <div className="col-span-2">
        <UniversalChart
          type="line"
          variant="management"
          data={sampleChartData}
          series={[
            { key: 'revenue', name: 'Revenue', color: '#4f46e5' },
            { key: 'commissions', name: 'Commissions', color: '#10b981' }
          ]}
          xAxis={{ dataKey: 'name' }}
          yAxis={{ left: { label: 'Amount ($)' } }}
          showLegend={true}
          showGrid={true}
          height={300}
          aspectRatio={2}
          onDataPointClick={() => {}}
          onLegendClick={() => {}}
          title="Revenue & Commissions Trend"
          subtitle="Monthly performance tracking"
        />
      </div>

      {/* Performance Metrics */}
      <div className="col-span-2">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold mb-4">Performance Overview</h3>
          <div className="space-y-4">
            {sampleMetrics.map((metric) => (
              <UniversalMetricCard
                key={metric.id}
                title={metric.title}
                value={metric.value}
                subtitle="Current period"
                trend={metric.trend}
                variant="compact"
                icon={undefined}
                progress={{ current: 75, target: 100 }}
                status={{ type: 'neutral' }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Top Partners Table */}
      <div className="col-span-4">
        <UniversalDataTable
          data={sampleTableData}
          columns={tableColumns}
          paginated={true}
          sortable={true}
          filterable={true}
          searchable={true}
          pageSize={10}
          actions={[
            {
              id: 'view-details',
              label: 'View Details',
              onClick: (row: any) => console.log('View details for:', row.partner)
            },
            {
              id: 'process-commission',
              label: 'Process Commission',
              onClick: (row: any) => console.log('Process commission for:', row.partner)
            }
          ]}
          onSelectionChange={() => {}}
          onRowClick={() => {}}
          onSort={() => {}}
          onFilter={() => {}}
          onSearch={() => {}}
          onExport={() => {}}
          onBulkAction={() => {}}
          maxHeight="500px"
        />
      </div>

      {/* Quick Actions */}
      <div className="col-span-4">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
          <div className="flex flex-wrap gap-4">
            <Button
              variant="outline"
              onClick={() => console.log('Add new partner')}
            >
              Add New Partner
            </Button>
            <Button
              variant="outline"
              onClick={() => console.log('Process payouts')}
            >
              Process Payouts
            </Button>
            <Button
              variant="outline"
              onClick={() => console.log('Generate reports')}
            >
              Generate Reports
            </Button>
            <Button
              variant="outline"
              onClick={() => console.log('Territory management')}
            >
              Territory Management
            </Button>
          </div>
        </div>
      </div>
    </UniversalDashboard>
  );
}
