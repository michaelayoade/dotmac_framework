/**
 * Work Order Management Component
 * 
 * Comprehensive work order management interface with creation, editing,
 * assignment, tracking, and analytics capabilities.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Plus, Search, Filter, Download, Calendar, MapPin, User,
  Clock, CheckCircle, AlertTriangle, Edit, Trash2, Eye,
  Navigation, Phone, FileText, Settings, RefreshCw,
  BarChart3, Target, Zap, Route
} from 'lucide-react';

// Types
interface WorkOrder {
  id: string;
  work_order_number: string;
  title: string;
  description: string;
  work_order_type: string;
  status: string;
  priority: string;
  customer_id?: string;
  customer_name?: string;
  customer_phone?: string;
  customer_email?: string;
  service_address: string;
  access_instructions?: string;
  scheduled_date?: string;
  scheduled_time_start?: string;
  estimated_duration?: number;
  technician?: Technician;
  progress_percentage: number;
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
}

interface Technician {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  skill_level: string;
  current_status: string;
  is_available: boolean;
  current_workload: number;
  jobs_completed_today: number;
  average_job_rating?: number;
}

interface WorkOrderFilter {
  status?: string[];
  priority?: string[];
  type?: string[];
  technician?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}

interface CreateWorkOrderForm {
  title: string;
  description: string;
  work_order_type: string;
  priority: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  service_address: string;
  access_instructions: string;
  scheduled_date: string;
  scheduled_time_start: string;
  estimated_duration: number;
}

const WorkOrderManagement: React.FC = () => {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [selectedWorkOrder, setSelectedWorkOrder] = useState<WorkOrder | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<WorkOrderFilter>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);

  // Form state
  const [createForm, setCreateForm] = useState<CreateWorkOrderForm>({
    title: '',
    description: '',
    work_order_type: 'installation',
    priority: 'normal',
    customer_name: '',
    customer_phone: '',
    customer_email: '',
    service_address: '',
    access_instructions: '',
    scheduled_date: '',
    scheduled_time_start: '',
    estimated_duration: 120
  });

  // Load work orders
  const loadWorkOrders = useCallback(async (appliedFilters?: WorkOrderFilter) => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      
      if (appliedFilters?.status?.length) {
        appliedFilters.status.forEach(status => params.append('status', status));
      }
      if (appliedFilters?.priority?.length) {
        appliedFilters.priority.forEach(priority => params.append('priority', priority));
      }
      if (appliedFilters?.type?.length) {
        appliedFilters.type.forEach(type => params.append('type', type));
      }
      if (appliedFilters?.technician) {
        params.append('technician_id', appliedFilters.technician);
      }
      if (appliedFilters?.date_from) {
        params.append('date_from', appliedFilters.date_from);
      }
      if (appliedFilters?.date_to) {
        params.append('date_to', appliedFilters.date_to);
      }
      if (appliedFilters?.search) {
        params.append('search', appliedFilters.search);
      }

      const response = await fetch(`/api/v1/field-operations/work-orders?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load work orders');
      }

      const workOrdersData = await response.json();
      setWorkOrders(workOrdersData);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load work orders');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load technicians
  const loadTechnicians = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/field-operations/technicians', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const techData = await response.json();
        setTechnicians(techData);
      }
    } catch (err) {
      console.error('Failed to load technicians:', err);
    }
  }, []);

  useEffect(() => {
    loadWorkOrders(filters);
    loadTechnicians();
  }, [loadWorkOrders, loadTechnicians, filters]);

  // Create work order
  const handleCreateWorkOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await fetch('/api/v1/field-operations/work-orders', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...createForm,
          estimated_duration: Number(createForm.estimated_duration)
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create work order');
      }

      const newWorkOrder = await response.json();
      setWorkOrders(prev => [newWorkOrder, ...prev]);
      setShowCreateModal(false);
      
      // Reset form
      setCreateForm({
        title: '',
        description: '',
        work_order_type: 'installation',
        priority: 'normal',
        customer_name: '',
        customer_phone: '',
        customer_email: '',
        service_address: '',
        access_instructions: '',
        scheduled_date: '',
        scheduled_time_start: '',
        estimated_duration: 120
      });

      alert('Work order created successfully!');

    } catch (err) {
      alert(`Failed to create work order: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Assign technician
  const handleAssignTechnician = async (workOrderId: string, technicianId: string) => {
    try {
      const response = await fetch(
        `/api/v1/field-operations/work-orders/${workOrderId}/assign/${technicianId}`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Assignment failed');
      }

      // Refresh work orders
      loadWorkOrders(filters);
      alert('Technician assigned successfully!');

    } catch (err) {
      alert(`Assignment failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Intelligent dispatch
  const handleIntelligentDispatch = async (workOrderId: string) => {
    try {
      const response = await fetch(
        `/api/v1/field-operations/work-orders/${workOrderId}/dispatch/intelligent`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Intelligent dispatch failed');
      }

      const assignedTech = await response.json();
      loadWorkOrders(filters);
      alert(`Intelligently assigned to ${assignedTech.full_name}`);

    } catch (err) {
      alert(`Intelligent dispatch failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Apply filters
  const handleApplyFilters = (newFilters: WorkOrderFilter) => {
    setFilters(newFilters);
    setCurrentPage(1);
  };

  // Filtered and paginated work orders
  const filteredWorkOrders = useMemo(() => {
    let filtered = workOrders;

    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(wo =>
        wo.title.toLowerCase().includes(searchLower) ||
        wo.work_order_number.toLowerCase().includes(searchLower) ||
        wo.customer_name?.toLowerCase().includes(searchLower) ||
        wo.service_address.toLowerCase().includes(searchLower)
      );
    }

    return filtered;
  }, [workOrders, filters.search]);

  const paginatedWorkOrders = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredWorkOrders.slice(startIndex, endIndex);
  }, [filteredWorkOrders, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filteredWorkOrders.length / itemsPerPage);

  // Get status color
  const getStatusColor = (status: string) => {
    const colors = {
      'draft': 'bg-gray-100 text-gray-800',
      'scheduled': 'bg-blue-100 text-blue-800',
      'dispatched': 'bg-yellow-100 text-yellow-800',
      'on_site': 'bg-green-100 text-green-800',
      'in_progress': 'bg-blue-100 text-blue-800',
      'completed': 'bg-green-100 text-green-800',
      'cancelled': 'bg-red-100 text-red-800',
      'requires_followup': 'bg-orange-100 text-orange-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityColor = (priority: string) => {
    const colors = {
      'emergency': 'text-red-600',
      'urgent': 'text-red-500',
      'high': 'text-orange-500',
      'normal': 'text-gray-600',
      'low': 'text-gray-400'
    };
    return colors[priority] || 'text-gray-600';
  };

  if (loading && workOrders.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading work orders...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Work Order Management</h1>
              <p className="text-gray-600">Manage and track all field service work orders</p>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center px-3 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
              >
                <Filter className="h-4 w-4 mr-2" />
                Filters
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Work Order
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters Panel */}
        {showFilters && (
          <div className="bg-white rounded-lg shadow mb-6 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Filters</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
                <input
                  type="text"
                  value={filters.search || ''}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                  placeholder="Search work orders..."
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  multiple
                  value={filters.status || []}
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions, option => option.value);
                    setFilters(prev => ({ ...prev, status: values }));
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                >
                  <option value="draft">Draft</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="dispatched">Dispatched</option>
                  <option value="on_site">On Site</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                <select
                  multiple
                  value={filters.priority || []}
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions, option => option.value);
                    setFilters(prev => ({ ...prev, priority: values }));
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                  <option value="emergency">Emergency</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Technician</label>
                <select
                  value={filters.technician || ''}
                  onChange={(e) => setFilters(prev => ({ ...prev, technician: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                >
                  <option value="">All Technicians</option>
                  {technicians.map(tech => (
                    <option key={tech.id} value={tech.id}>{tech.full_name}</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="mt-4 flex items-center space-x-4">
              <button
                onClick={() => handleApplyFilters(filters)}
                className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
              >
                Apply Filters
              </button>
              <button
                onClick={() => {
                  setFilters({});
                  handleApplyFilters({});
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded text-sm hover:bg-gray-50"
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}

        {/* Work Orders Table */}
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">
              Work Orders ({filteredWorkOrders.length})
            </h3>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => loadWorkOrders(filters)}
                className="p-2 text-gray-400 hover:text-gray-600"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
              <button className="p-2 text-gray-400 hover:text-gray-600">
                <Download className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Work Order
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Customer
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Location
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Technician
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Schedule
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {paginatedWorkOrders.map((workOrder) => (
                  <tr key={workOrder.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="flex items-center">
                          <div className={`h-2 w-2 rounded-full mr-2 ${getPriorityColor(workOrder.priority)}`} 
                               style={{ backgroundColor: 'currentColor' }}></div>
                          <p className="text-sm font-medium text-gray-900">
                            {workOrder.work_order_number}
                          </p>
                        </div>
                        <p className="text-sm text-gray-500">{workOrder.title}</p>
                        <p className="text-xs text-gray-400">{workOrder.work_order_type}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{workOrder.customer_name}</p>
                        {workOrder.customer_phone && (
                          <div className="flex items-center text-sm text-gray-500">
                            <Phone className="h-3 w-3 mr-1" />
                            <a href={`tel:${workOrder.customer_phone}`} className="hover:text-blue-600">
                              {workOrder.customer_phone}
                            </a>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-500">
                        <MapPin className="h-3 w-3 mr-1 flex-shrink-0" />
                        <span className="truncate max-w-xs">{workOrder.service_address}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {workOrder.technician ? (
                        <div>
                          <p className="text-sm font-medium text-gray-900">{workOrder.technician.full_name}</p>
                          <p className="text-xs text-gray-500">{workOrder.technician.skill_level}</p>
                        </div>
                      ) : (
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-gray-400">Unassigned</span>
                          <button
                            onClick={() => handleIntelligentDispatch(workOrder.id)}
                            className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded"
                          >
                            Auto Assign
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {workOrder.scheduled_date && (
                          <div className="flex items-center">
                            <Calendar className="h-3 w-3 mr-1" />
                            {new Date(workOrder.scheduled_date).toLocaleDateString()}
                          </div>
                        )}
                        {workOrder.scheduled_time_start && (
                          <div className="flex items-center text-xs text-gray-500">
                            <Clock className="h-3 w-3 mr-1" />
                            {new Date(`2000-01-01T${workOrder.scheduled_time_start}`).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-col space-y-1">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(workOrder.status)}`}>
                          {workOrder.status.replace('_', ' ')}
                        </span>
                        {workOrder.is_overdue && (
                          <span className="text-xs text-red-600">Overdue</span>
                        )}
                        <div className="w-16 bg-gray-200 rounded-full h-1">
                          <div
                            className="bg-blue-600 h-1 rounded-full transition-all"
                            style={{ width: `${workOrder.progress_percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => setSelectedWorkOrder(workOrder)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button className="text-gray-400 hover:text-gray-600">
                          <Edit className="h-4 w-4" />
                        </button>
                        <button className="text-red-400 hover:text-red-600">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-3 flex items-center justify-between border-t border-gray-200">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing{' '}
                    <span className="font-medium">{(currentPage - 1) * itemsPerPage + 1}</span>
                    {' '}to{' '}
                    <span className="font-medium">
                      {Math.min(currentPage * itemsPerPage, filteredWorkOrders.length)}
                    </span>
                    {' '}of{' '}
                    <span className="font-medium">{filteredWorkOrders.length}</span>
                    {' '}results
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Previous
                    </button>
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                          currentPage === page
                            ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                            : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                        }`}
                      >
                        {page}
                      </button>
                    ))}
                    <button
                      onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                      disabled={currentPage === totalPages}
                      className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Work Order Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>
            
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleCreateWorkOrder}>
                <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Work Order</h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
                      <input
                        type="text"
                        required
                        value={createForm.title}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, title: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
                      <textarea
                        required
                        rows={3}
                        value={createForm.description}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                        <select
                          value={createForm.work_order_type}
                          onChange={(e) => setCreateForm(prev => ({ ...prev, work_order_type: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                        >
                          <option value="installation">Installation</option>
                          <option value="maintenance">Maintenance</option>
                          <option value="repair">Repair</option>
                          <option value="upgrade">Upgrade</option>
                          <option value="inspection">Inspection</option>
                          <option value="disconnect">Disconnect</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                        <select
                          value={createForm.priority}
                          onChange={(e) => setCreateForm(prev => ({ ...prev, priority: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                        >
                          <option value="low">Low</option>
                          <option value="normal">Normal</option>
                          <option value="high">High</option>
                          <option value="urgent">Urgent</option>
                          <option value="emergency">Emergency</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Customer Name *</label>
                      <input
                        type="text"
                        required
                        value={createForm.customer_name}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, customer_name: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Customer Phone</label>
                        <input
                          type="tel"
                          value={createForm.customer_phone}
                          onChange={(e) => setCreateForm(prev => ({ ...prev, customer_phone: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Customer Email</label>
                        <input
                          type="email"
                          value={createForm.customer_email}
                          onChange={(e) => setCreateForm(prev => ({ ...prev, customer_email: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Service Address *</label>
                      <input
                        type="text"
                        required
                        value={createForm.service_address}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, service_address: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Scheduled Date</label>
                        <input
                          type="date"
                          value={createForm.scheduled_date}
                          onChange={(e) => setCreateForm(prev => ({ ...prev, scheduled_date: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
                        <input
                          type="time"
                          value={createForm.scheduled_time_start}
                          onChange={(e) => setCreateForm(prev => ({ ...prev, scheduled_time_start: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Estimated Duration (minutes)</label>
                      <input
                        type="number"
                        min="15"
                        max="1440"
                        value={createForm.estimated_duration}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, estimated_duration: parseInt(e.target.value) }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                      />
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                  <button
                    type="submit"
                    className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                  >
                    Create Work Order
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkOrderManagement;