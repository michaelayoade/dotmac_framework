'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { useProvisioning } from '@dotmac/headless';
import { 
  useNotifications,
  VirtualizedTable,
  Modal 
} from '@dotmac/primitives';

interface ProvisioningDashboardProps {
  className?: string;
}

export function ProvisioningDashboard({ className = '' }: ProvisioningDashboardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'requests' | 'templates' | 'calendar'>('overview');
  const [selectedRequests, setSelectedRequests] = useState<string[]>([]);
  const [showNewRequestModal, setShowNewRequestModal] = useState(false);
  const [requestFilters, setRequestFilters] = useState({
    status: '',
    priority: '',
    dateFrom: '',
    dateTo: '',
  });

  const provisioning = useProvisioning({
    websocketEndpoint: process.env.NEXT_PUBLIC_WS_URL,
    apiKey: process.env.NEXT_PUBLIC_API_KEY,
    enableRealtime: true,
    pollInterval: 30000,
  });

  const { addNotification } = useNotifications();

  // Quick Actions
  const handleBulkApproval = useCallback(async () => {
    if (selectedRequests.length === 0) return;
    
    try {
      await provisioning.bulkUpdateStatus(selectedRequests, 'approved', 'Bulk approved');
      setSelectedRequests([]);
      
      addNotification({
        type: 'success',
        priority: 'medium',
        title: 'Bulk Approval Complete',
        message: `${selectedRequests.length} requests approved`,
        channel: ['browser'],
        persistent: false,
      });
    } catch (error) {
      console.error('Failed to bulk approve requests:', error);
    }
  }, [provisioning, selectedRequests, addNotification]);

  const handleQuickSchedule = useCallback(async (requestId: string) => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(9, 0, 0, 0); // 9 AM tomorrow

    try {
      await provisioning.scheduleInstallation(requestId, tomorrow);
    } catch (error) {
      console.error('Failed to schedule installation:', error);
    }
  }, [provisioning]);

  // Filtered data
  const filteredRequests = useMemo(() => {
    return provisioning.requests.filter(request => {
      if (requestFilters.status && request.status !== requestFilters.status) return false;
      if (requestFilters.priority && request.priority !== requestFilters.priority) return false;
      if (requestFilters.dateFrom && request.requestedAt < new Date(requestFilters.dateFrom)) return false;
      if (requestFilters.dateTo && request.requestedAt > new Date(requestFilters.dateTo)) return false;
      return true;
    });
  }, [provisioning.requests, requestFilters]);

  const stats = provisioning.stats || {
    totalRequests: 0,
    pendingRequests: 0,
    activeInstallations: 0,
    completedToday: 0,
    averageProvisioningTime: 0,
    successRate: 0,
    slaCompliance: 0,
    statusBreakdown: {},
    technicianWorkload: {},
    upcomingInstallations: [],
  };

  return (
    <div className={`provisioning-dashboard ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">Service Provisioning</h1>
          <div className="flex items-center space-x-2">
            {provisioning.isConnected ? (
              <div className="flex items-center space-x-1 text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm">Live Updates</span>
              </div>
            ) : (
              <div className="flex items-center space-x-1 text-red-600">
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <span className="text-sm">Offline</span>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          {selectedRequests.length > 0 && (
            <button
              onClick={handleBulkApproval}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              Approve {selectedRequests.length} Requests
            </button>
          )}
          <button
            onClick={() => setShowNewRequestModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            disabled={provisioning.isLoading}
          >
            New Service Request
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Pending Requests</p>
              <p className="text-2xl font-bold text-orange-600">{stats.pendingRequests}</p>
            </div>
            <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
              <span className="text-orange-600">⏳</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Active Installations</p>
              <p className="text-2xl font-bold text-blue-600">{stats.activeInstallations}</p>
            </div>
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-600">🔧</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Completed Today</p>
              <p className="text-2xl font-bold text-green-600">{stats.completedToday}</p>
            </div>
            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
              <span className="text-green-600">✅</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">SLA Compliance</p>
              <p className="text-2xl font-bold text-purple-600">{stats.slaCompliance.toFixed(1)}%</p>
            </div>
            <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
              <span className="text-purple-600">📊</span>
            </div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">
              Avg: {stats.averageProvisioningTime.toFixed(1)}h
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'requests', label: 'Service Requests', count: provisioning.requests.length },
            { id: 'templates', label: 'Service Templates', count: provisioning.templates.length },
            { id: 'calendar', label: 'Installation Calendar' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`
                py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className="ml-2 bg-gray-100 text-gray-900 py-0.5 px-2.5 rounded-full text-xs">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'overview' && (
          <OverviewTab
            stats={stats}
            urgentRequests={provisioning.urgentRequests}
            todayInstallations={provisioning.todayInstallations}
            onSelectRequest={provisioning.selectRequest}
          />
        )}

        {activeTab === 'requests' && (
          <RequestsTab
            requests={filteredRequests}
            filters={requestFilters}
            onFiltersChange={setRequestFilters}
            selectedRequests={selectedRequests}
            onSelectionChange={setSelectedRequests}
            onUpdateStatus={provisioning.updateRequestStatus}
            onScheduleInstallation={provisioning.scheduleInstallation}
            onQuickSchedule={handleQuickSchedule}
            onCancel={provisioning.cancelRequest}
            isLoading={provisioning.isLoading}
          />
        )}

        {activeTab === 'templates' && (
          <TemplatesTab
            templates={provisioning.templates}
            onCreateRequest={(templateId, customerInfo) => {
              // This would open a modal or form to create a new request
              console.log('Create request for template:', templateId, customerInfo);
            }}
          />
        )}

        {activeTab === 'calendar' && (
          <CalendarTab
            installations={stats.upcomingInstallations}
            onReschedule={provisioning.scheduleInstallation}
          />
        )}
      </div>

      {/* New Request Modal */}
      {showNewRequestModal && (
        <NewRequestModal
          templates={provisioning.templates}
          onSubmit={async (requestData) => {
            try {
              await provisioning.createServiceRequest(requestData);
              setShowNewRequestModal(false);
            } catch (error) {
              console.error('Failed to create request:', error);
            }
          }}
          onClose={() => setShowNewRequestModal(false)}
        />
      )}
    </div>
  );
}

// Overview Tab Component
interface OverviewTabProps {
  stats: any;
  urgentRequests: any[];
  todayInstallations: any[];
  onSelectRequest: (request: any) => void;
}

function OverviewTab({ 
  stats, 
  urgentRequests, 
  todayInstallations, 
  onSelectRequest 
}: OverviewTabProps) {
  return (
    <div className="overview-tab">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Breakdown Chart */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Status Breakdown</h2>
          <div className="space-y-3">
            {Object.entries(stats.statusBreakdown).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 capitalize">{status.replace('_', ' ')}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-16 bg-gray-200 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full bg-blue-600" 
                      style={{ width: `${(count as number / stats.totalRequests) * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-900">{count as number}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Technician Workload */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Technician Workload</h2>
          <div className="space-y-3">
            {Object.entries(stats.technicianWorkload).slice(0, 5).map(([technician, workload]) => (
              <div key={technician} className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{technician}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-16 bg-gray-200 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full bg-orange-600" 
                      style={{ width: `${Math.min((workload as number / 10) * 100, 100)}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-900">{workload as number}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Urgent Requests */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Urgent Requests ({urgentRequests.length})
          </h2>
          <div className="space-y-3">
            {urgentRequests.slice(0, 5).map((request) => (
              <div 
                key={request.id}
                className="flex items-center justify-between p-3 border border-red-200 rounded-lg bg-red-50 cursor-pointer hover:bg-red-100"
                onClick={() => onSelectRequest(request)}
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{request.customerInfo.name}</p>
                  <p className="text-xs text-gray-500">{request.serviceTemplateId}</p>
                </div>
                <span className="text-xs bg-red-600 text-white px-2 py-1 rounded-full">
                  {request.status}
                </span>
              </div>
            ))}
            {urgentRequests.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">No urgent requests</p>
            )}
          </div>
        </div>

        {/* Today's Installations */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Today's Installations ({todayInstallations.length})
          </h2>
          <div className="space-y-3">
            {todayInstallations.slice(0, 5).map((installation) => (
              <div 
                key={installation.id}
                className="flex items-center justify-between p-3 border border-blue-200 rounded-lg bg-blue-50 cursor-pointer hover:bg-blue-100"
                onClick={() => onSelectRequest(installation)}
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{installation.customerInfo.name}</p>
                  <p className="text-xs text-gray-500">
                    {installation.scheduledAt ? new Date(installation.scheduledAt).toLocaleTimeString() : 'Not scheduled'}
                  </p>
                </div>
                <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded-full">
                  {installation.assignedTechnician || 'Unassigned'}
                </span>
              </div>
            ))}
            {todayInstallations.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">No installations today</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Requests Tab Component
interface RequestsTabProps {
  requests: any[];
  filters: any;
  onFiltersChange: (filters: any) => void;
  selectedRequests: string[];
  onSelectionChange: (ids: string[]) => void;
  onUpdateStatus: (id: string, status: string, notes?: string) => Promise<any>;
  onScheduleInstallation: (id: string, date: Date, technicianId?: string) => Promise<any>;
  onQuickSchedule: (id: string) => Promise<void>;
  onCancel: (id: string, reason: string) => Promise<void>;
  isLoading: boolean;
}

function RequestsTab({ 
  requests, 
  filters, 
  onFiltersChange, 
  selectedRequests, 
  onSelectionChange,
  onUpdateStatus,
  onScheduleInstallation,
  onQuickSchedule,
  onCancel,
  isLoading 
}: RequestsTabProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'text-yellow-600 bg-yellow-50';
      case 'approved': return 'text-green-600 bg-green-50';
      case 'provisioning': return 'text-blue-600 bg-blue-50';
      case 'installing': return 'text-purple-600 bg-purple-50';
      case 'active': return 'text-green-600 bg-green-50';
      case 'failed': return 'text-red-600 bg-red-50';
      case 'cancelled': return 'text-gray-600 bg-gray-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-red-600 bg-red-50';
      case 'high': return 'text-orange-600 bg-orange-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const columns = [
    {
      key: 'select',
      header: (
        <input
          type="checkbox"
          checked={selectedRequests.length === requests.length && requests.length > 0}
          onChange={(e) => {
            if (e.target.checked) {
              onSelectionChange(requests.map(req => req.id));
            } else {
              onSelectionChange([]);
            }
          }}
          className="rounded border-gray-300"
        />
      ),
      render: (request: any) => (
        <input
          type="checkbox"
          checked={selectedRequests.includes(request.id)}
          onChange={(e) => {
            if (e.target.checked) {
              onSelectionChange([...selectedRequests, request.id]);
            } else {
              onSelectionChange(selectedRequests.filter(id => id !== request.id));
            }
          }}
          className="rounded border-gray-300"
        />
      ),
    },
    {
      key: 'customer',
      header: 'Customer',
      render: (request: any) => (
        <div>
          <p className="font-medium text-gray-900">{request.customerInfo.name}</p>
          <p className="text-sm text-gray-500">{request.customerInfo.email}</p>
        </div>
      ),
    },
    {
      key: 'service',
      header: 'Service',
      render: (request: any) => (
        <span className="text-sm text-gray-900">{request.serviceTemplateId}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (request: any) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
          {request.status}
        </span>
      ),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (request: any) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(request.priority)}`}>
          {request.priority}
        </span>
      ),
    },
    {
      key: 'requested',
      header: 'Requested',
      render: (request: any) => (
        <span className="text-sm text-gray-500">
          {new Date(request.requestedAt).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'scheduled',
      header: 'Scheduled',
      render: (request: any) => (
        <span className="text-sm text-gray-500">
          {request.scheduledAt 
            ? new Date(request.scheduledAt).toLocaleDateString()
            : 'Not scheduled'
          }
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (request: any) => (
        <div className="flex space-x-2">
          {request.status === 'pending' && (
            <button
              onClick={() => onUpdateStatus(request.id, 'approved')}
              className="text-green-600 hover:text-green-900 text-sm"
            >
              Approve
            </button>
          )}
          {['approved', 'provisioning'].includes(request.status) && !request.scheduledAt && (
            <button
              onClick={() => onQuickSchedule(request.id)}
              className="text-blue-600 hover:text-blue-900 text-sm"
            >
              Schedule
            </button>
          )}
          {request.status === 'pending' && (
            <button
              onClick={() => onCancel(request.id, 'Cancelled by reseller')}
              className="text-red-600 hover:text-red-900 text-sm"
            >
              Cancel
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="requests-tab">
      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => onFiltersChange({ ...filters, status: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="provisioning">Provisioning</option>
              <option value="installing">Installing</option>
              <option value="active">Active</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
            <select
              value={filters.priority}
              onChange={(e) => onFiltersChange({ ...filters, priority: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Priorities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => onFiltersChange({ ...filters, dateFrom: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => onFiltersChange({ ...filters, dateTo: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Requests Table */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-500">Loading requests...</p>
          </div>
        ) : requests.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-gray-400 text-4xl mb-4">📋</div>
            <p className="text-gray-500">No service requests found</p>
          </div>
        ) : (
          <VirtualizedTable
            data={requests}
            columns={columns}
            height={600}
            rowHeight={60}
            className="w-full"
          />
        )}
      </div>
    </div>
  );
}

// Templates Tab Component
interface TemplatesTabProps {
  templates: any[];
  onCreateRequest: (templateId: string, customerInfo: any) => void;
}

function TemplatesTab({ templates, onCreateRequest }: TemplatesTabProps) {
  return (
    <div className="templates-tab">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {templates.map((template) => (
          <div key={template.id} className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">{template.name}</h3>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                template.category === 'internet' ? 'bg-blue-100 text-blue-800' :
                template.category === 'phone' ? 'bg-green-100 text-green-800' :
                template.category === 'tv' ? 'bg-purple-100 text-purple-800' :
                'bg-orange-100 text-orange-800'
              }`}>
                {template.category}
              </span>
            </div>

            <div className="space-y-2 mb-4">
              {template.speed && (
                <p className="text-sm text-gray-600">Speed: <span className="font-medium">{template.speed}</span></p>
              )}
              <p className="text-sm text-gray-600">Setup: <span className="font-medium">${template.pricing.setup}</span></p>
              <p className="text-sm text-gray-600">Monthly: <span className="font-medium">${template.pricing.monthly}</span></p>
              <p className="text-sm text-gray-600">SLA: <span className="font-medium">{template.sla.provisioningTime}h</span></p>
            </div>

            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Features</h4>
              <div className="flex flex-wrap gap-1">
                {template.features.slice(0, 3).map((feature: string) => (
                  <span key={feature} className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs">
                    {feature}
                  </span>
                ))}
                {template.features.length > 3 && (
                  <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs">
                    +{template.features.length - 3} more
                  </span>
                )}
              </div>
            </div>

            <button
              onClick={() => onCreateRequest(template.id, {})}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
            >
              Create Request
            </button>
          </div>
        ))}
      </div>

      {templates.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-4xl mb-4">🛠️</div>
          <p className="text-gray-500">No service templates available.</p>
        </div>
      )}
    </div>
  );
}

// Calendar Tab Component
interface CalendarTabProps {
  installations: any[];
  onReschedule: (id: string, date: Date, technicianId?: string) => Promise<any>;
}

function CalendarTab({ installations, onReschedule }: CalendarTabProps) {
  const [selectedDate, setSelectedDate] = useState(new Date());

  // Group installations by date
  const installationsByDate = installations.reduce((acc, installation) => {
    if (!installation.scheduledAt) return acc;
    
    const date = new Date(installation.scheduledAt).toDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(installation);
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <div className="calendar-tab">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar View */}
        <div className="lg:col-span-2 bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Installation Calendar</h2>
          
          {/* Simple calendar implementation */}
          <div className="calendar-grid">
            {Object.entries(installationsByDate).map(([date, dayInstallations]) => (
              <div key={date} className="mb-4">
                <h3 className="font-medium text-gray-900 mb-2">
                  {new Date(date).toLocaleDateString(undefined, { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  })}
                </h3>
                <div className="space-y-2">
                  {dayInstallations.map((installation) => (
                    <div key={installation.id} className="p-3 border border-blue-200 rounded-lg bg-blue-50">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-gray-900">{installation.customerInfo.name}</p>
                          <p className="text-sm text-gray-600">{installation.serviceTemplateId}</p>
                          <p className="text-xs text-gray-500">
                            {new Date(installation.scheduledAt).toLocaleTimeString()}
                          </p>
                        </div>
                        <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded-full">
                          {installation.assignedTechnician || 'Unassigned'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {Object.keys(installationsByDate).length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 text-4xl mb-4">📅</div>
              <p className="text-gray-500">No installations scheduled.</p>
            </div>
          )}
        </div>

        {/* Today's Summary */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Today's Schedule</h2>
          
          <div className="space-y-3">
            {installations
              .filter(inst => inst.scheduledAt && 
                new Date(inst.scheduledAt).toDateString() === new Date().toDateString()
              )
              .map((installation) => (
                <div key={installation.id} className="p-3 border border-green-200 rounded-lg bg-green-50">
                  <p className="font-medium text-gray-900">{installation.customerInfo.name}</p>
                  <p className="text-sm text-gray-600">{installation.serviceTemplateId}</p>
                  <p className="text-xs text-gray-500">
                    {new Date(installation.scheduledAt).toLocaleTimeString()}
                  </p>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// New Request Modal Component
interface NewRequestModalProps {
  templates: any[];
  onSubmit: (requestData: any) => Promise<void>;
  onClose: () => void;
}

function NewRequestModal({ templates, onSubmit, onClose }: NewRequestModalProps) {
  const [formData, setFormData] = useState({
    customerId: '',
    serviceTemplateId: '',
    priority: 'medium' as const,
    customerName: '',
    customerEmail: '',
    customerPhone: '',
    installationStreet: '',
    installationCity: '',
    installationState: '',
    installationZip: '',
    notes: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const requestData = {
      customerId: formData.customerId || `customer_${Date.now()}`,
      serviceTemplateId: formData.serviceTemplateId,
      priority: formData.priority,
      installationAddress: {
        street: formData.installationStreet,
        city: formData.installationCity,
        state: formData.installationState,
        zip: formData.installationZip,
      },
      customerInfo: {
        name: formData.customerName,
        email: formData.customerEmail,
        phone: formData.customerPhone,
      },
      notes: formData.notes,
    };

    await onSubmit(requestData);
  };

  return (
    <Modal onClose={onClose} className="max-w-2xl">
      <div className="p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">New Service Request</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Service Template</label>
              <select
                value={formData.serviceTemplateId}
                onChange={(e) => setFormData({ ...formData, serviceTemplateId: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              >
                <option value="">Select service...</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name} - ${template.pricing.monthly}/mo
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value as any })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Customer Name</label>
              <input
                type="text"
                value={formData.customerName}
                onChange={(e) => setFormData({ ...formData, customerName: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Customer Email</label>
              <input
                type="email"
                value={formData.customerEmail}
                onChange={(e) => setFormData({ ...formData, customerEmail: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Customer Phone</label>
              <input
                type="tel"
                value={formData.customerPhone}
                onChange={(e) => setFormData({ ...formData, customerPhone: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Street Address</label>
              <input
                type="text"
                value={formData.installationStreet}
                onChange={(e) => setFormData({ ...formData, installationStreet: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
              <input
                type="text"
                value={formData.installationCity}
                onChange={(e) => setFormData({ ...formData, installationCity: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
              <input
                type="text"
                value={formData.installationState}
                onChange={(e) => setFormData({ ...formData, installationState: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">ZIP Code</label>
              <input
                type="text"
                value={formData.installationZip}
                onChange={(e) => setFormData({ ...formData, installationZip: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={3}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
            >
              Create Request
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}

export default ProvisioningDashboard;