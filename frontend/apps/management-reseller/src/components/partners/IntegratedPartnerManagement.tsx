'use client';

import { UniversalDataTable, UniversalChart } from '@dotmac/primitives';
import { Button, Modal } from '@dotmac/primitives';
import { useState } from 'react';

// Sample partner data - replace with real API
const samplePartners = [
  {
    id: 1,
    name: 'TechNet Solutions',
    status: 'Active',
    revenue: 450000,
    commission: 45000,
    region: 'West Coast',
    joinDate: '2023-01-15',
    lastActivity: '2024-01-28',
    tier: 'Gold',
    contacts: 3,
    territories: 5
  },
  {
    id: 2,
    name: 'ConnectCorp',
    status: 'Active',
    revenue: 380000,
    commission: 38000,
    region: 'East Coast',
    joinDate: '2023-03-22',
    lastActivity: '2024-01-29',
    tier: 'Silver',
    contacts: 2,
    territories: 3
  },
  {
    id: 3,
    name: 'NetWorks Inc',
    status: 'Under Review',
    revenue: 520000,
    commission: 52000,
    region: 'Central',
    joinDate: '2022-11-08',
    lastActivity: '2024-01-27',
    tier: 'Platinum',
    contacts: 5,
    territories: 8
  },
  {
    id: 4,
    name: 'ISP Partners',
    status: 'Active',
    revenue: 290000,
    commission: 29000,
    region: 'South',
    joinDate: '2023-06-10',
    lastActivity: '2024-01-25',
    tier: 'Bronze',
    contacts: 1,
    territories: 2
  },
  {
    id: 5,
    name: 'Digital Bridge',
    status: 'Pending Approval',
    revenue: 670000,
    commission: 67000,
    region: 'Northwest',
    joinDate: '2023-12-01',
    lastActivity: '2024-01-29',
    tier: 'Platinum',
    contacts: 4,
    territories: 6
  }
];

const partnerColumns = [
  { key: 'name', label: 'Partner Name', sortable: true },
  {
    key: 'status',
    label: 'Status',
    sortable: true,
    render: (value: string) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
        value === 'Active' ? 'bg-green-100 text-green-800' :
        value === 'Under Review' ? 'bg-yellow-100 text-yellow-800' :
        'bg-gray-100 text-gray-800'
      }`}>
        {value}
      </span>
    )
  },
  {
    key: 'revenue',
    label: 'Revenue',
    sortable: true,
    render: (value: number) => `$${(value / 1000).toFixed(0)}K`
  },
  {
    key: 'commission',
    label: 'Commission',
    sortable: true,
    render: (value: number) => `$${(value / 1000).toFixed(0)}K`
  },
  { key: 'region', label: 'Region', sortable: true },
  {
    key: 'tier',
    label: 'Tier',
    sortable: true,
    render: (value: string) => (
      <span className={`px-2 py-1 rounded text-xs font-medium ${
        value === 'Platinum' ? 'bg-purple-100 text-purple-800' :
        value === 'Gold' ? 'bg-yellow-100 text-yellow-800' :
        value === 'Silver' ? 'bg-gray-100 text-gray-800' :
        'bg-orange-100 text-orange-800'
      }`}>
        {value}
      </span>
    )
  },
  { key: 'territories', label: 'Territories', sortable: true }
];

// Chart data for partner performance
const performanceData = [
  { month: 'Jan', revenue: 1680000, partners: 45 },
  { month: 'Feb', revenue: 1720000, partners: 47 },
  { month: 'Mar', revenue: 1890000, partners: 52 },
  { month: 'Apr', revenue: 2100000, partners: 58 },
  { month: 'May', revenue: 2240000, partners: 61 },
  { month: 'Jun', revenue: 2310000, partners: 64 }
];

export function IntegratedPartnerManagement() {
  const [selectedPartner, setSelectedPartner] = useState<any>(null);
  const [showPartnerModal, setShowPartnerModal] = useState(false);

  const handleViewPartner = (partner: any) => {
    setSelectedPartner(partner);
    setShowPartnerModal(true);
  };

  const handleApprovePartner = (partner: any) => {
    console.log('Approving partner:', partner.name);
    // Implementation for approval
  };

  const handleSuspendPartner = (partner: any) => {
    console.log('Suspending partner:', partner.name);
    // Implementation for suspension
  };

  const tableActions = [
    {
      id: 'view-details',
      label: 'View Details',
      onClick: handleViewPartner
    },
    {
      id: 'approve',
      label: 'Approve',
      onClick: handleApprovePartner,
      condition: (row: any) => row.status === 'Pending Approval'
    },
    {
      id: 'suspend',
      label: 'Suspend',
      onClick: handleSuspendPartner,
      condition: (row: any) => row.status === 'Active'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Partner Management</h1>
          <p className="text-gray-600">Manage reseller partnerships and performance</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">
            Export Data
          </Button>
          <Button>
            Add New Partner
          </Button>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <UniversalChart
          type="combo"
          variant="management"
          data={performanceData}
          series={[
            {
              key: 'revenue',
              name: 'Total Revenue',
              type: 'line',
              color: '#4f46e5',
              yAxisId: 'left'
            },
            {
              key: 'partners',
              name: 'Active Partners',
              type: 'bar',
              color: '#10b981',
              yAxisId: 'right'
            }
          ]}
          xAxis={{ dataKey: 'month' }}
          yAxis={{
            left: { label: 'Revenue ($)' },
            right: { label: 'Partners' }
          }}
          showLegend={true}
          showGrid={true}
          height={300}
        />
      </div>

      {/* Partners Table */}
      <div className="bg-white rounded-lg shadow-sm border">
        <UniversalDataTable
          data={samplePartners}
          columns={partnerColumns}
          paginated={true}
          sortable={true}
          filterable={true}
          searchable={true}
          exportable={true}
          selectable={true}
          pageSize={10}
          actions={tableActions}
        />
      </div>

      {/* Partner Details Modal */}
      <Modal
        isOpen={showPartnerModal}
        onClose={() => setShowPartnerModal(false)}
        title={`Partner Details - ${selectedPartner?.name}`}
        size="large"
      >
        {selectedPartner && (
          <div className="space-y-6">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Partner Name
                </label>
                <p className="text-gray-900">{selectedPartner.name}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  selectedPartner.status === 'Active' ? 'bg-green-100 text-green-800' :
                  selectedPartner.status === 'Under Review' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {selectedPartner.status}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Region
                </label>
                <p className="text-gray-900">{selectedPartner.region}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tier Level
                </label>
                <p className="text-gray-900">{selectedPartner.tier}</p>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-900">
                  ${(selectedPartner.revenue / 1000).toFixed(0)}K
                </p>
                <p className="text-sm text-gray-600">Total Revenue</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-900">
                  ${(selectedPartner.commission / 1000).toFixed(0)}K
                </p>
                <p className="text-sm text-gray-600">Commission Earned</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-900">
                  {selectedPartner.territories}
                </p>
                <p className="text-sm text-gray-600">Territories</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => setShowPartnerModal(false)}
              >
                Close
              </Button>
              {selectedPartner.status === 'Pending Approval' && (
                <Button onClick={() => handleApprovePartner(selectedPartner)}>
                  Approve Partner
                </Button>
              )}
              {selectedPartner.status === 'Active' && (
                <Button
                  variant="destructive"
                  onClick={() => handleSuspendPartner(selectedPartner)}
                >
                  Suspend Partner
                </Button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
