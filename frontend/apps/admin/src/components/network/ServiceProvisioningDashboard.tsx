'use client';

import { useState, useEffect } from 'react';
import {
  Plus,
  Clock,
  CheckCircle,
  AlertTriangle,
  X,
  Eye,
  MapPin,
  User,
  Wifi,
  Globe,
  Settings,
  Calendar,
  FileText,
  Zap,
  Wrench,
  Play,
} from 'lucide-react';
import { ServiceProvisioningWorkflow } from '../provisioning';

interface ProvisioningRequest {
  id: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  serviceAddress: string;
  serviceType: 'residential_fiber' | 'business_fiber' | 'enterprise_dedicated' | 'bulk_service';
  planName: string;
  speed: { download: number; upload: number };
  requestDate: string;
  targetDate: string;
  status: 'pending' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled' | 'blocked';
  priority: 'low' | 'normal' | 'high' | 'critical';
  assignedTechnician?: string;
  territory: string;
  requirements: string[];
  blockers?: string[];
  progress: {
    step: string;
    completed: boolean;
    notes?: string;
  }[];
  estimatedDuration: number; // in hours
  cost: {
    equipment: number;
    labor: number;
    materials: number;
  };
}

interface ServiceProvisioningDashboardProps {
  requests?: ProvisioningRequest[];
  onRequestSelect?: (request: ProvisioningRequest) => void;
  onStatusUpdate?: (requestId: string, status: string) => void;
}

const mockRequests: ProvisioningRequest[] = [
  {
    id: 'PROV-2024-001',
    customerId: 'CUST-1234',
    customerName: 'Sarah Chen',
    customerEmail: 'sarah.chen@example.com',
    serviceAddress: '456 Maple Street, Seattle, WA 98105',
    serviceType: 'residential_fiber',
    planName: 'DotMac Fiber 500/500',
    speed: { download: 500, upload: 500 },
    requestDate: '2024-02-18T10:30:00Z',
    targetDate: '2024-02-25T14:00:00Z',
    status: 'scheduled',
    priority: 'normal',
    assignedTechnician: 'TECH-003',
    territory: 'Seattle Central',
    requirements: ['Fiber drop installation', 'ONT placement', 'Router configuration'],
    progress: [
      { step: 'Site survey completed', completed: true, notes: 'Clean install path confirmed' },
      { step: 'Permits obtained', completed: true },
      { step: 'Equipment staged', completed: false },
      { step: 'Installation scheduled', completed: false },
      { step: 'Service activation', completed: false },
    ],
    estimatedDuration: 4,
    cost: { equipment: 450, labor: 280, materials: 120 },
  },
  {
    id: 'PROV-2024-002',
    customerId: 'CUST-5678',
    customerName: 'TechStart Inc.',
    customerEmail: 'it@techstart.com',
    serviceAddress: '1200 Corporate Plaza, Bellevue, WA 98004',
    serviceType: 'business_fiber',
    planName: 'DotMac Business Pro 1Gbps',
    speed: { download: 1000, upload: 1000 },
    requestDate: '2024-02-15T09:15:00Z',
    targetDate: '2024-02-28T10:00:00Z',
    status: 'in_progress',
    priority: 'high',
    assignedTechnician: 'TECH-001',
    territory: 'Eastside',
    requirements: [
      'Dedicated fiber run',
      'Enterprise router setup',
      'SLA configuration',
      'Static IP allocation',
    ],
    progress: [
      { step: 'Site survey completed', completed: true },
      { step: 'Fiber run completed', completed: true },
      { step: 'Equipment installation', completed: true },
      { step: 'Network configuration', completed: false },
      { step: 'Testing and validation', completed: false },
    ],
    estimatedDuration: 8,
    cost: { equipment: 1200, labor: 640, materials: 300 },
  },
  {
    id: 'PROV-2024-003',
    customerId: 'CUST-9012',
    customerName: 'Oakwood Apartments',
    customerEmail: 'manager@oakwoodapts.com',
    serviceAddress: '800 Pine Avenue, Kirkland, WA 98033',
    serviceType: 'bulk_service',
    planName: 'Bulk Fiber Service (32 units)',
    speed: { download: 1000, upload: 1000 },
    requestDate: '2024-02-10T14:20:00Z',
    targetDate: '2024-03-15T12:00:00Z',
    status: 'blocked',
    priority: 'high',
    assignedTechnician: 'TECH-002',
    territory: 'Eastside',
    requirements: [
      'Bulk fiber installation',
      'Building wiring',
      'MDU equipment setup',
      'Unit provisioning',
    ],
    blockers: ['Building permit delayed', 'HOA approval pending'],
    progress: [
      { step: 'Building assessment', completed: true },
      { step: 'Permits and approvals', completed: false, notes: 'Waiting on city permit' },
      { step: 'Equipment procurement', completed: false },
      { step: 'Installation', completed: false },
      { step: 'Unit activation', completed: false },
    ],
    estimatedDuration: 40,
    cost: { equipment: 8500, labor: 3200, materials: 1800 },
  },
  {
    id: 'PROV-2024-004',
    customerId: 'CUST-3456',
    customerName: 'DataFlow Solutions',
    customerEmail: 'netops@dataflow.com',
    serviceAddress: '2000 Enterprise Way, Seattle, WA 98109',
    serviceType: 'enterprise_dedicated',
    planName: 'Enterprise Dedicated 10Gbps',
    speed: { download: 10000, upload: 10000 },
    requestDate: '2024-02-12T11:45:00Z',
    targetDate: '2024-03-10T09:00:00Z',
    status: 'pending',
    priority: 'critical',
    territory: 'Downtown',
    requirements: [
      'Dedicated dark fiber',
      '10G enterprise router',
      'Redundant paths',
      'BGP configuration',
      '24/7 monitoring',
    ],
    progress: [
      { step: 'Enterprise consultation', completed: true },
      { step: 'Network design', completed: false },
      { step: 'Fiber route planning', completed: false },
      { step: 'Equipment procurement', completed: false },
      { step: 'Installation and testing', completed: false },
    ],
    estimatedDuration: 80,
    cost: { equipment: 25000, labor: 6400, materials: 3500 },
  },
];

export function ServiceProvisioningDashboard({
  requests = mockRequests,
  onRequestSelect,
  onStatusUpdate,
}: ServiceProvisioningDashboardProps) {
  const [selectedRequest, setSelectedRequest] = useState<ProvisioningRequest | null>(null);
  const [showWorkflow, setShowWorkflow] = useState(false);
  const [workflowRequest, setWorkflowRequest] = useState<ProvisioningRequest | null>(null);
  const [filter, setFilter] = useState<'all' | 'pending' | 'scheduled' | 'in_progress' | 'blocked'>(
    'all'
  );
  const [sortBy, setSortBy] = useState<'priority' | 'target_date' | 'status'>('priority');

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'in_progress':
        return 'text-blue-600 bg-blue-100';
      case 'scheduled':
        return 'text-purple-600 bg-purple-100';
      case 'pending':
        return 'text-yellow-600 bg-yellow-100';
      case 'blocked':
        return 'text-red-600 bg-red-100';
      case 'cancelled':
        return 'text-gray-600 bg-gray-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'text-red-600 bg-red-100';
      case 'high':
        return 'text-orange-600 bg-orange-100';
      case 'normal':
        return 'text-blue-600 bg-blue-100';
      case 'low':
        return 'text-gray-600 bg-gray-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getServiceTypeIcon = (type: string) => {
    switch (type) {
      case 'residential_fiber':
        return User;
      case 'business_fiber':
        return Globe;
      case 'enterprise_dedicated':
        return Zap;
      case 'bulk_service':
        return Wifi;
      default:
        return Settings;
    }
  };

  const filteredRequests = requests
    .filter((request) => filter === 'all' || request.status === filter)
    .sort((a, b) => {
      if (sortBy === 'priority') {
        const priorityOrder = { critical: 0, high: 1, normal: 2, low: 3 };
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      }
      if (sortBy === 'target_date') {
        return new Date(a.targetDate).getTime() - new Date(b.targetDate).getTime();
      }
      return a.status.localeCompare(b.status);
    });

  const getProgressPercentage = (progress: ProvisioningRequest['progress']) => {
    const completed = progress.filter((step) => step.completed).length;
    return Math.round((completed / progress.length) * 100);
  };

  const handleRequestClick = (request: ProvisioningRequest) => {
    setSelectedRequest(request);
    onRequestSelect?.(request);
  };

  const handleStatusUpdate = (requestId: string, newStatus: string) => {
    onStatusUpdate?.(requestId, newStatus);
  };

  const handleStartWorkflow = (request: ProvisioningRequest) => {
    setWorkflowRequest(request);
    setShowWorkflow(true);
  };

  const handleWorkflowComplete = (result: any) => {
    console.log('Workflow completed for request:', workflowRequest?.id, result);
    setShowWorkflow(false);
    setWorkflowRequest(null);
    // Update request status to completed
    handleStatusUpdate(workflowRequest?.id || '', 'completed');
  };

  const handleWorkflowCancel = () => {
    setShowWorkflow(false);
    setWorkflowRequest(null);
  };

  const stats = {
    total: requests.length,
    pending: requests.filter((r) => r.status === 'pending').length,
    scheduled: requests.filter((r) => r.status === 'scheduled').length,
    in_progress: requests.filter((r) => r.status === 'in_progress').length,
    blocked: requests.filter((r) => r.status === 'blocked').length,
    completed_this_week: requests.filter((r) => r.status === 'completed').length, // Mock data
  };

  // Show workflow if started
  if (showWorkflow && workflowRequest) {
    return (
      <div className="min-h-screen bg-gray-50">
        <ServiceProvisioningWorkflow
          onComplete={handleWorkflowComplete}
          onCancel={handleWorkflowCancel}
          requestId={workflowRequest.id}
          customerInfo={{
            name: workflowRequest.customerName,
            email: workflowRequest.customerEmail,
            address: workflowRequest.serviceAddress
          }}
          serviceType={workflowRequest.serviceType}
        />
      </div>
    );
  }

  return (
    <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
      <div className='flex justify-between items-center mb-6'>
        <div>
          <h3 className='text-lg font-semibold text-gray-900'>Service Provisioning</h3>
          <p className='text-sm text-gray-600'>Manage service installations and activations</p>
        </div>

        <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2'>
          <Plus className='h-4 w-4' />
          New Request
        </button>
      </div>

      {/* Stats Overview */}
      <div className='grid grid-cols-2 md:grid-cols-6 gap-4 mb-6'>
        <div className='bg-gray-50 rounded-lg p-3'>
          <div className='text-2xl font-bold text-gray-900'>{stats.total}</div>
          <div className='text-xs text-gray-600'>Total Requests</div>
        </div>
        <div className='bg-yellow-50 rounded-lg p-3'>
          <div className='text-2xl font-bold text-yellow-600'>{stats.pending}</div>
          <div className='text-xs text-gray-600'>Pending</div>
        </div>
        <div className='bg-purple-50 rounded-lg p-3'>
          <div className='text-2xl font-bold text-purple-600'>{stats.scheduled}</div>
          <div className='text-xs text-gray-600'>Scheduled</div>
        </div>
        <div className='bg-blue-50 rounded-lg p-3'>
          <div className='text-2xl font-bold text-blue-600'>{stats.in_progress}</div>
          <div className='text-xs text-gray-600'>In Progress</div>
        </div>
        <div className='bg-red-50 rounded-lg p-3'>
          <div className='text-2xl font-bold text-red-600'>{stats.blocked}</div>
          <div className='text-xs text-gray-600'>Blocked</div>
        </div>
        <div className='bg-green-50 rounded-lg p-3'>
          <div className='text-2xl font-bold text-green-600'>{stats.completed_this_week}</div>
          <div className='text-xs text-gray-600'>Completed This Week</div>
        </div>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
        {/* Requests List */}
        <div className='lg:col-span-2'>
          <div className='flex gap-2 mb-4'>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className='text-sm border border-gray-300 rounded px-2 py-1'
            >
              <option value='all'>All Status</option>
              <option value='pending'>Pending</option>
              <option value='scheduled'>Scheduled</option>
              <option value='in_progress'>In Progress</option>
              <option value='blocked'>Blocked</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className='text-sm border border-gray-300 rounded px-2 py-1'
            >
              <option value='priority'>Sort by Priority</option>
              <option value='target_date'>Sort by Target Date</option>
              <option value='status'>Sort by Status</option>
            </select>
          </div>

          <div className='space-y-3 max-h-96 overflow-y-auto'>
            {filteredRequests.map((request) => {
              const Icon = getServiceTypeIcon(request.serviceType);
              const progress = getProgressPercentage(request.progress);

              return (
                <div
                  key={request.id}
                  className={`border rounded-lg p-4 cursor-pointer transition-all ${
                    selectedRequest?.id === request.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => handleRequestClick(request)}
                >
                  <div className='flex items-start justify-between mb-2'>
                    <div className='flex items-center gap-2'>
                      <Icon className='h-5 w-5 text-gray-600' />
                      <div>
                        <h4 className='font-medium text-gray-900'>{request.customerName}</h4>
                        <p className='text-sm text-gray-600'>{request.planName}</p>
                      </div>
                    </div>

                    <div className='flex gap-2'>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(request.priority)}`}
                      >
                        {request.priority}
                      </span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}
                      >
                        {request.status}
                      </span>
                    </div>
                  </div>

                  <div className='flex items-center gap-4 text-sm text-gray-600 mb-2'>
                    <div className='flex items-center gap-1'>
                      <MapPin className='h-4 w-4' />
                      <span>{request.territory}</span>
                    </div>
                    <div className='flex items-center gap-1'>
                      <Calendar className='h-4 w-4' />
                      <span>{new Date(request.targetDate).toLocaleDateString()}</span>
                    </div>
                    <div className='flex items-center gap-1'>
                      <Clock className='h-4 w-4' />
                      <span>{request.estimatedDuration}h</span>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className='mb-2'>
                    <div className='flex justify-between text-xs text-gray-600 mb-1'>
                      <span>Progress</span>
                      <span>{progress}%</span>
                    </div>
                    <div className='w-full bg-gray-200 rounded-full h-2'>
                      <div
                        className={`h-2 rounded-full transition-all ${
                          progress === 100
                            ? 'bg-green-500'
                            : progress > 50
                              ? 'bg-blue-500'
                              : 'bg-yellow-500'
                        }`}
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                  </div>

                  {request.blockers && request.blockers.length > 0 && (
                    <div className='flex items-center gap-1 text-xs text-red-600'>
                      <AlertTriangle className='h-3 w-3' />
                      <span>{request.blockers.length} blocker(s)</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Request Details */}
        <div>
          {selectedRequest ? (
            <div className='bg-gray-50 rounded-lg p-4'>
              <div className='flex items-center justify-between mb-4'>
                <h4 className='font-medium text-gray-900'>Request Details</h4>
                <button
                  onClick={() => setSelectedRequest(null)}
                  className='text-gray-400 hover:text-gray-600'
                >
                  <X className='h-4 w-4' />
                </button>
              </div>

              <div className='space-y-4 text-sm'>
                <div>
                  <span className='text-gray-600'>Customer:</span>
                  <p className='font-medium'>{selectedRequest.customerName}</p>
                  <p className='text-xs text-gray-500'>{selectedRequest.customerEmail}</p>
                </div>

                <div>
                  <span className='text-gray-600'>Service Address:</span>
                  <p className='font-medium'>{selectedRequest.serviceAddress}</p>
                </div>

                <div>
                  <span className='text-gray-600'>Service Plan:</span>
                  <p className='font-medium'>{selectedRequest.planName}</p>
                  <p className='text-xs text-gray-500'>
                    {selectedRequest.speed.download}/{selectedRequest.speed.upload} Mbps
                  </p>
                </div>

                <div>
                  <span className='text-gray-600'>Target Date:</span>
                  <p className='font-medium'>
                    {new Date(selectedRequest.targetDate).toLocaleDateString()}
                  </p>
                </div>

                {selectedRequest.assignedTechnician && (
                  <div>
                    <span className='text-gray-600'>Assigned Technician:</span>
                    <p className='font-medium'>{selectedRequest.assignedTechnician}</p>
                  </div>
                )}

                <div>
                  <span className='text-gray-600'>Cost Estimate:</span>
                  <div className='mt-1 space-y-1 text-xs'>
                    <div className='flex justify-between'>
                      <span>Equipment:</span>
                      <span>${selectedRequest.cost.equipment}</span>
                    </div>
                    <div className='flex justify-between'>
                      <span>Labor:</span>
                      <span>${selectedRequest.cost.labor}</span>
                    </div>
                    <div className='flex justify-between'>
                      <span>Materials:</span>
                      <span>${selectedRequest.cost.materials}</span>
                    </div>
                    <div className='flex justify-between font-medium border-t pt-1'>
                      <span>Total:</span>
                      <span>
                        $
                        {selectedRequest.cost.equipment +
                          selectedRequest.cost.labor +
                          selectedRequest.cost.materials}
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <span className='text-gray-600'>Requirements:</span>
                  <ul className='mt-1 space-y-1'>
                    {selectedRequest.requirements.map((req, index) => (
                      <li key={index} className='text-xs bg-white rounded px-2 py-1'>
                        {req}
                      </li>
                    ))}
                  </ul>
                </div>

                {selectedRequest.blockers && selectedRequest.blockers.length > 0 && (
                  <div>
                    <span className='text-red-600'>Blockers:</span>
                    <ul className='mt-1 space-y-1'>
                      {selectedRequest.blockers.map((blocker, index) => (
                        <li
                          key={index}
                          className='text-xs bg-red-50 text-red-700 rounded px-2 py-1'
                        >
                          {blocker}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <span className='text-gray-600'>Progress Steps:</span>
                  <div className='mt-2 space-y-2'>
                    {selectedRequest.progress.map((step, index) => (
                      <div key={index} className='flex items-start gap-2'>
                        {step.completed ? (
                          <CheckCircle className='h-4 w-4 text-green-600 mt-0.5' />
                        ) : (
                          <Clock className='h-4 w-4 text-gray-400 mt-0.5' />
                        )}
                        <div className='flex-1'>
                          <div
                            className={`text-xs ${step.completed ? 'text-green-700' : 'text-gray-600'}`}
                          >
                            {step.step}
                          </div>
                          {step.notes && (
                            <div className='text-xs text-gray-500 mt-1'>{step.notes}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className='pt-4 border-t space-y-2'>
                  <button
                    onClick={() => handleStartWorkflow(selectedRequest)}
                    className='w-full px-3 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700'
                  >
                    <Play className='h-4 w-4 inline mr-1' />
                    Start Workflow
                  </button>
                  <button className='w-full px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700'>
                    <Eye className='h-4 w-4 inline mr-1' />
                    View Full Details
                  </button>
                  <button className='w-full px-3 py-2 border border-gray-300 text-gray-700 text-sm rounded hover:bg-gray-50'>
                    <Wrench className='h-4 w-4 inline mr-1' />
                    Update Status
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className='bg-gray-50 rounded-lg p-4 text-center text-gray-500'>
              <FileText className='h-8 w-8 mx-auto mb-2 text-gray-400' />
              <p className='text-sm'>Select a provisioning request to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
