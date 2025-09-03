/**
 * Dispatch Dashboard Component
 * 
 * Real-time dashboard for field operations dispatch management.
 * Shows technicians, work orders, and intelligent assignment capabilities.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  MapPin, Clock, User, AlertTriangle, CheckCircle, 
  Navigation, Battery, Phone, Settings, Filter,
  Calendar, Target, TrendingUp, Zap, Route
} from 'lucide-react';

// Types
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
  current_location?: {
    latitude: number;
    longitude: number;
  };
  last_active?: string;
}

interface WorkOrder {
  id: string;
  work_order_number: string;
  title: string;
  work_order_type: string;
  status: string;
  priority: string;
  customer_name?: string;
  service_address: string;
  scheduled_date?: string;
  technician?: Technician;
  progress_percentage: number;
  is_overdue: boolean;
  estimated_duration?: number;
}

interface DashboardSummary {
  date: string;
  work_orders: {
    total: number;
    by_status: Record<string, number>;
    completed_today: number;
    in_progress: number;
    overdue: number;
  };
  technicians: {
    total: number;
    available: number;
    on_job: number;
    off_duty: number;
  };
}

const DispatchDashboard: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [selectedTechnician, setSelectedTechnician] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    status: 'all',
    priority: 'all',
    type: 'all'
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load dashboard data
  const loadDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Load summary data
      const summaryResponse = await fetch('/api/v1/field-operations/dashboard/summary', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!summaryResponse.ok) {
        throw new Error('Failed to load dashboard summary');
      }

      const summaryData = await summaryResponse.json();
      setSummary(summaryData);

      // Load available technicians
      const techResponse = await fetch('/api/v1/field-operations/technicians', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (techResponse.ok) {
        const techData = await techResponse.json();
        setTechnicians(techData);
      }

      // Load today's work orders
      const woResponse = await fetch('/api/v1/field-operations/work-orders?date=' + new Date().toISOString().split('T')[0], {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (woResponse.ok) {
        const woData = await woResponse.json();
        setWorkOrders(woData);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
    
    // Refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, [loadDashboardData]);

  // Intelligent dispatch handler
  const handleIntelligentDispatch = async (workOrderId: string) => {
    try {
      const response = await fetch(`/api/v1/field-operations/work-orders/${workOrderId}/dispatch/intelligent`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Dispatch failed');
      }

      const assignedTech = await response.json();
      
      // Show success notification
      alert(`Work order successfully assigned to ${assignedTech.full_name}`);
      
      // Refresh data
      loadDashboardData();
      
    } catch (err) {
      alert(`Dispatch failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Emergency dispatch handler
  const handleEmergencyDispatch = async (workOrderId: string) => {
    if (!confirm('This will immediately dispatch the nearest available technician. Continue?')) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/field-operations/work-orders/${workOrderId}/dispatch/emergency`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Emergency dispatch failed');
      }

      const assignedTech = await response.json();
      
      alert(`Emergency dispatch successful! Assigned to ${assignedTech.full_name}`);
      loadDashboardData();
      
    } catch (err) {
      alert(`Emergency dispatch failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    const colors = {
      'available': 'text-green-600 bg-green-100',
      'on_job': 'text-blue-600 bg-blue-100',
      'traveling': 'text-yellow-600 bg-yellow-100',
      'off_duty': 'text-gray-600 bg-gray-100',
      'scheduled': 'text-blue-600 bg-blue-100',
      'in_progress': 'text-green-600 bg-green-100',
      'completed': 'text-green-600 bg-green-100',
      'overdue': 'text-red-600 bg-red-100',
      'high': 'text-orange-600 bg-orange-100',
      'urgent': 'text-red-600 bg-red-100',
      'emergency': 'text-red-600 bg-red-200'
    };
    return colors[status.toLowerCase()] || 'text-gray-600 bg-gray-100';
  };

  // Get priority icon
  const getPriorityIcon = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'emergency':
        return <Zap className="h-4 w-4 text-red-600" />;
      case 'urgent':
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'high':
        return <Target className="h-4 w-4 text-orange-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-600" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dispatch dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-600 mx-auto" />
          <p className="mt-4 text-red-600">Error: {error}</p>
          <button
            onClick={loadDashboardData}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
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
              <h1 className="text-2xl font-bold text-gray-900">Field Operations Dispatch</h1>
              <p className="text-gray-600">{new Date().toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}</p>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={loadDashboardData}
                className="flex items-center px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Refresh
              </button>
              <Settings className="h-6 w-6 text-gray-600 cursor-pointer" />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Calendar className="h-8 w-8 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Today's Work Orders</p>
                  <p className="text-2xl font-bold text-gray-900">{summary.work_orders.total}</p>
                  <p className="text-sm text-green-600">{summary.work_orders.completed_today} completed</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <User className="h-8 w-8 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Available Technicians</p>
                  <p className="text-2xl font-bold text-gray-900">{summary.technicians.available}</p>
                  <p className="text-sm text-gray-600">of {summary.technicians.total} total</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <TrendingUp className="h-8 w-8 text-orange-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">In Progress</p>
                  <p className="text-2xl font-bold text-gray-900">{summary.work_orders.in_progress}</p>
                  <p className="text-sm text-blue-600">{summary.technicians.on_job} on job</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <AlertTriangle className="h-8 w-8 text-red-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Overdue Jobs</p>
                  <p className="text-2xl font-bold text-gray-900">{summary.work_orders.overdue}</p>
                  <p className="text-sm text-red-600">Needs attention</p>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Technicians Panel */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Field Technicians</h3>
            </div>
            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {technicians.map((technician) => (
                <div
                  key={technician.id}
                  className={`p-4 cursor-pointer hover:bg-gray-50 ${
                    selectedTechnician === technician.id ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => setSelectedTechnician(technician.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0">
                        <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                          <User className="h-6 w-6 text-gray-600" />
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{technician.full_name}</p>
                        <p className="text-sm text-gray-500">{technician.skill_level}</p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end space-y-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(technician.current_status)}`}>
                        {technician.current_status.replace('_', ' ')}
                      </span>
                      {technician.is_available && (
                        <div className="flex items-center text-xs text-gray-500">
                          <Battery className="h-3 w-3 mr-1" />
                          {100 - technician.current_workload}% capacity
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                    <div className="flex items-center space-x-4">
                      <span>{technician.jobs_completed_today} jobs today</span>
                      {technician.average_job_rating && (
                        <span>★ {technician.average_job_rating.toFixed(1)}</span>
                      )}
                    </div>
                    {technician.last_active && (
                      <span>Last active: {new Date(technician.last_active).toLocaleTimeString()}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Work Orders Panel */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Unassigned Work Orders</h3>
              <Filter className="h-5 w-5 text-gray-400" />
            </div>
            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {workOrders
                .filter(wo => !wo.technician)
                .map((workOrder) => (
                <div key={workOrder.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        {getPriorityIcon(workOrder.priority)}
                        <h4 className="text-sm font-medium text-gray-900">
                          {workOrder.work_order_number}
                        </h4>
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(workOrder.status)}`}>
                          {workOrder.status.replace('_', ' ')}
                        </span>
                      </div>
                      
                      <p className="text-sm text-gray-600 mt-1">{workOrder.title}</p>
                      
                      <div className="flex items-center mt-2 text-xs text-gray-500">
                        <MapPin className="h-3 w-3 mr-1" />
                        <span className="truncate">{workOrder.service_address}</span>
                      </div>
                      
                      {workOrder.customer_name && (
                        <div className="flex items-center mt-1 text-xs text-gray-500">
                          <Phone className="h-3 w-3 mr-1" />
                          <span>{workOrder.customer_name}</span>
                        </div>
                      )}
                    </div>
                    
                    <div className="ml-4 flex flex-col space-y-2">
                      <button
                        onClick={() => handleIntelligentDispatch(workOrder.id)}
                        className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        Auto Assign
                      </button>
                      
                      {workOrder.priority === 'emergency' && (
                        <button
                          onClick={() => handleEmergencyDispatch(workOrder.id)}
                          className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                        >
                          Emergency
                        </button>
                      )}
                      
                      <button className="px-3 py-1 text-xs border border-gray-300 text-gray-700 rounded hover:bg-gray-50">
                        Manual
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Route Optimization Section */}
        <div className="mt-8 bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Route Optimization</h3>
              <Route className="h-5 w-5 text-gray-400" />
            </div>
          </div>
          <div className="p-6">
            <p className="text-gray-600 mb-4">
              Optimize technician routes to minimize travel time and maximize efficiency.
            </p>
            <div className="flex space-x-4">
              <button className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
                Optimize All Routes
              </button>
              <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50">
                View Route Analytics
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DispatchDashboard;