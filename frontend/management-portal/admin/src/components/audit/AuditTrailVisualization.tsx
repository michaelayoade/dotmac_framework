/**
 * Audit Trail Visualization Component
 * Connects to the existing dotmac_shared audit logging framework
 * Provides comprehensive audit log exploration and compliance reporting
 */

import React, { useState, useEffect } from 'react';
import {
  DocumentTextIcon,
  FunnelIcon,
  CalendarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  UserIcon,
  ClockIcon,
  EyeIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/http';

interface AuditEvent {
  id: string;
  timestamp: string;
  event_type: string;
  user_id?: string;
  user_email?: string;
  tenant_id?: string;
  resource_type: string;
  resource_id: string;
  action: string;
  details: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  session_id?: string;
  outcome: 'success' | 'failure' | 'error';
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  compliance_tags: string[];
}

interface AuditFilters {
  dateRange: {
    start: string;
    end: string;
  };
  eventTypes: string[];
  users: string[];
  tenants: string[];
  outcomes: string[];
  riskLevels: string[];
  searchQuery: string;
}

interface AuditTrailVisualizationProps {
  className?: string;
}

export function AuditTrailVisualization({ className = '' }: AuditTrailVisualizationProps) {
  const [filters, setFilters] = useState<AuditFilters>({
    dateRange: {
      start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      end: new Date().toISOString().split('T')[0],
    },
    eventTypes: [],
    users: [],
    tenants: [],
    outcomes: [],
    riskLevels: [],
    searchQuery: '',
  });

  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [viewMode, setViewMode] = useState<'table' | 'timeline' | 'analytics'>('table');

  // Fetch audit events
  const {
    data: auditData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['audit-events', filters],
    queryFn: async () => {
      const params: Record<string, string> = {
        start_date: filters.dateRange.start,
        end_date: filters.dateRange.end,
        search: filters.searchQuery,
      };
      if (filters.eventTypes.length > 0) params.event_types = filters.eventTypes.join(',');
      if (filters.users.length > 0) params.users = filters.users.join(',');
      if (filters.tenants.length > 0) params.tenants = filters.tenants.join(',');
      if (filters.outcomes.length > 0) params.outcomes = filters.outcomes.join(',');
      if (filters.riskLevels.length > 0) params.risk_levels = filters.riskLevels.join(',');

      const res = await api.get(`/api/v1/audit/events`, { params });
      return res.data;
    },
  });

  // Fetch filter options
  const { data: filterOptions } = useQuery({
    queryKey: ['audit-filter-options'],
    queryFn: async () => {
      const res = await api.get(`/api/v1/audit/filter-options`);
      return res.data;
    },
  });

  const getOutcomeIcon = (outcome: string) => {
    switch (outcome) {
      case 'success':
        return <CheckCircleIcon className='h-5 w-5 text-green-500' />;
      case 'failure':
        return <XCircleIcon className='h-5 w-5 text-red-500' />;
      case 'error':
        return <ExclamationTriangleIcon className='h-5 w-5 text-orange-500' />;
      default:
        return <ClockIcon className='h-5 w-5 text-gray-500' />;
    }
  };

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const handleExportAuditLog = async () => {
    const params = new URLSearchParams({
      start_date: filters.dateRange.start,
      end_date: filters.dateRange.end,
      format: 'csv',
    });

    const res = await api.get(`/api/v1/audit/export`, { params, responseType: 'blob' as any });
    if (res.status === 200) {
      const blob = res.data as unknown as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-log-${filters.dateRange.start}-${filters.dateRange.end}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  if (isLoading) {
    return (
      <div className={`flex justify-center items-center py-12 ${className}`}>
        <LoadingSpinner size='large' />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <ExclamationTriangleIcon className='mx-auto h-12 w-12 text-red-500' />
        <h3 className='mt-4 text-lg font-medium text-gray-900'>Error Loading Audit Trail</h3>
        <p className='mt-2 text-gray-600'>Failed to load audit events. Please try again.</p>
      </div>
    );
  }

  const events = auditData?.events || [];
  const summary = auditData?.summary || {};

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Audit Trail</h1>
          <p className='text-gray-600 mt-1'>
            Comprehensive audit log exploration and compliance reporting
          </p>
        </div>

        <div className='flex items-center space-x-3'>
          <div className='flex rounded-md shadow-sm'>
            <button
              onClick={() => setViewMode('table')}
              className={`px-4 py-2 text-sm font-medium rounded-l-md border ${
                viewMode === 'table'
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              Table
            </button>
            <button
              onClick={() => setViewMode('timeline')}
              className={`px-4 py-2 text-sm font-medium border-t border-b ${
                viewMode === 'timeline'
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              Timeline
            </button>
            <button
              onClick={() => setViewMode('analytics')}
              className={`px-4 py-2 text-sm font-medium rounded-r-md border ${
                viewMode === 'analytics'
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              Analytics
            </button>
          </div>

          <button
            onClick={handleExportAuditLog}
            className='flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700'
          >
            <ArrowDownTrayIcon className='h-4 w-4' />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-600'>Total Events</p>
              <p className='text-3xl font-bold text-gray-900'>
                {summary.total_events || events.length}
              </p>
            </div>
            <DocumentTextIcon className='h-8 w-8 text-blue-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-600'>Success Rate</p>
              <p className='text-3xl font-bold text-green-600'>
                {summary.success_rate ? `${summary.success_rate}%` : 'N/A'}
              </p>
            </div>
            <CheckCircleIcon className='h-8 w-8 text-green-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-600'>High Risk Events</p>
              <p className='text-3xl font-bold text-red-600'>{summary.high_risk_events || 0}</p>
            </div>
            <ExclamationTriangleIcon className='h-8 w-8 text-red-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-600'>Unique Users</p>
              <p className='text-3xl font-bold text-gray-900'>{summary.unique_users || 0}</p>
            </div>
            <UserIcon className='h-8 w-8 text-gray-500' />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
        <div className='px-6 py-4 border-b border-gray-200'>
          <div className='flex items-center space-x-2'>
            <FunnelIcon className='h-5 w-5 text-gray-500' />
            <h3 className='text-lg font-medium text-gray-900'>Filters</h3>
          </div>
        </div>

        <div className='p-6 space-y-4'>
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
            {/* Date Range */}
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>Date Range</label>
              <div className='flex space-x-2'>
                <input
                  type='date'
                  value={filters.dateRange.start}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      dateRange: { ...prev.dateRange, start: e.target.value },
                    }))
                  }
                  className='flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                />
                <input
                  type='date'
                  value={filters.dateRange.end}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      dateRange: { ...prev.dateRange, end: e.target.value },
                    }))
                  }
                  className='flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                />
              </div>
            </div>

            {/* Search */}
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>Search</label>
              <div className='relative'>
                <MagnifyingGlassIcon className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
                <input
                  type='text'
                  placeholder='Search audit events...'
                  value={filters.searchQuery}
                  onChange={(e) => setFilters((prev) => ({ ...prev, searchQuery: e.target.value }))}
                  className='w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                />
              </div>
            </div>

            {/* Event Types */}
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>Event Types</label>
              <select
                multiple
                value={filters.eventTypes}
                onChange={(e) => {
                  const values = Array.from(e.target.selectedOptions, (option) => option.value);
                  setFilters((prev) => ({ ...prev, eventTypes: values }));
                }}
                className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
              >
                {filterOptions?.event_types?.map((type: string) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            {/* Risk Levels */}
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>Risk Level</label>
              <select
                multiple
                value={filters.riskLevels}
                onChange={(e) => {
                  const values = Array.from(e.target.selectedOptions, (option) => option.value);
                  setFilters((prev) => ({ ...prev, riskLevels: values }));
                }}
                className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
              >
                <option value='low'>Low</option>
                <option value='medium'>Medium</option>
                <option value='high'>High</option>
                <option value='critical'>Critical</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Event List/Timeline */}
      {viewMode === 'table' ? (
        <div className='bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden'>
          <table className='min-w-full divide-y divide-gray-200'>
            <thead className='bg-gray-50'>
              <tr>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Event
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  User
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Resource
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Outcome
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Risk
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Time
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className='bg-white divide-y divide-gray-200'>
              {events.map((event: AuditEvent) => (
                <tr key={event.id} className='hover:bg-gray-50'>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <div>
                      <div className='text-sm font-medium text-gray-900'>{event.event_type}</div>
                      <div className='text-sm text-gray-500'>{event.action}</div>
                    </div>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <div className='text-sm text-gray-900'>{event.user_email || 'System'}</div>
                    <div className='text-sm text-gray-500'>{event.ip_address}</div>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <div className='text-sm text-gray-900'>{event.resource_type}</div>
                    <div className='text-sm text-gray-500 truncate max-w-xs'>
                      {event.resource_id}
                    </div>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <div className='flex items-center'>
                      {getOutcomeIcon(event.outcome)}
                      <span className='ml-2 text-sm text-gray-900'>{event.outcome}</span>
                    </div>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRiskLevelColor(event.risk_level)}`}
                    >
                      {event.risk_level}
                    </span>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-500'>
                    {new Date(event.timestamp).toLocaleString()}
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap text-right text-sm font-medium'>
                    <button
                      onClick={() => setSelectedEvent(event)}
                      className='text-blue-600 hover:text-blue-900'
                    >
                      <EyeIcon className='h-4 w-4' />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : viewMode === 'analytics' ? (
        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <div className='flex items-center space-x-2 mb-6'>
            <ChartBarIcon className='h-5 w-5 text-gray-500' />
            <h3 className='text-lg font-medium text-gray-900'>Audit Analytics</h3>
          </div>

          <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
            <div className='space-y-4'>
              <h4 className='font-medium text-gray-900'>Event Types Distribution</h4>
              <div className='h-64 bg-gray-50 rounded-lg flex items-center justify-center'>
                <p className='text-gray-500'>Analytics charts will be implemented here</p>
              </div>
            </div>

            <div className='space-y-4'>
              <h4 className='font-medium text-gray-900'>Risk Level Trends</h4>
              <div className='h-64 bg-gray-50 rounded-lg flex items-center justify-center'>
                <p className='text-gray-500'>Risk trend charts will be implemented here</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <h3 className='text-lg font-medium text-gray-900 mb-4'>Timeline View</h3>
          <div className='space-y-4'>
            {events.map((event: AuditEvent) => (
              <div
                key={event.id}
                className='flex items-start space-x-4 border-l-4 border-blue-200 pl-4 py-3'
              >
                <div className='flex-shrink-0 mt-1'>{getOutcomeIcon(event.outcome)}</div>
                <div className='flex-1 min-w-0'>
                  <div className='flex items-center justify-between'>
                    <p className='text-sm font-medium text-gray-900'>
                      {event.event_type} - {event.action}
                    </p>
                    <p className='text-sm text-gray-500'>
                      {new Date(event.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <p className='text-sm text-gray-600'>
                    {event.user_email || 'System'} performed {event.action} on {event.resource_type}
                  </p>
                  <div className='mt-2 flex items-center space-x-4'>
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getRiskLevelColor(event.risk_level)}`}
                    >
                      {event.risk_level}
                    </span>
                    {event.compliance_tags?.length > 0 && (
                      <div className='flex space-x-1'>
                        {event.compliance_tags.map((tag: string) => (
                          <span
                            key={tag}
                            className='inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700'
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {events.length === 0 && (
        <div className='text-center py-12'>
          <DocumentTextIcon className='mx-auto h-12 w-12 text-gray-400' />
          <h3 className='mt-4 text-lg font-medium text-gray-900'>No Audit Events</h3>
          <p className='mt-2 text-gray-600'>No audit events found for the selected criteria.</p>
        </div>
      )}

      {/* Event Detail Modal */}
      {selectedEvent && (
        <div className='fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50'>
          <div className='relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white'>
            <div className='flex items-center justify-between mb-4'>
              <h3 className='text-lg font-medium text-gray-900'>Audit Event Details</h3>
              <button
                onClick={() => setSelectedEvent(null)}
                className='text-gray-400 hover:text-gray-600'
              >
                <XCircleIcon className='h-6 w-6' />
              </button>
            </div>

            <div className='space-y-4'>
              <div className='grid grid-cols-2 gap-4'>
                <div>
                  <label className='block text-sm font-medium text-gray-700'>Event Type</label>
                  <p className='mt-1 text-sm text-gray-900'>{selectedEvent.event_type}</p>
                </div>
                <div>
                  <label className='block text-sm font-medium text-gray-700'>Action</label>
                  <p className='mt-1 text-sm text-gray-900'>{selectedEvent.action}</p>
                </div>
                <div>
                  <label className='block text-sm font-medium text-gray-700'>User</label>
                  <p className='mt-1 text-sm text-gray-900'>
                    {selectedEvent.user_email || 'System'}
                  </p>
                </div>
                <div>
                  <label className='block text-sm font-medium text-gray-700'>Timestamp</label>
                  <p className='mt-1 text-sm text-gray-900'>
                    {new Date(selectedEvent.timestamp).toLocaleString()}
                  </p>
                </div>
                <div>
                  <label className='block text-sm font-medium text-gray-700'>Resource</label>
                  <p className='mt-1 text-sm text-gray-900'>
                    {selectedEvent.resource_type} - {selectedEvent.resource_id}
                  </p>
                </div>
                <div>
                  <label className='block text-sm font-medium text-gray-700'>Risk Level</label>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRiskLevelColor(selectedEvent.risk_level)}`}
                  >
                    {selectedEvent.risk_level}
                  </span>
                </div>
              </div>

              {selectedEvent.details && Object.keys(selectedEvent.details).length > 0 && (
                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Event Details
                  </label>
                  <pre className='mt-1 text-sm bg-gray-50 rounded-md p-4 overflow-x-auto'>
                    {JSON.stringify(selectedEvent.details, null, 2)}
                  </pre>
                </div>
              )}

              {selectedEvent.compliance_tags && selectedEvent.compliance_tags.length > 0 && (
                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Compliance Tags
                  </label>
                  <div className='flex flex-wrap gap-2'>
                    {selectedEvent.compliance_tags.map((tag: string) => (
                      <span
                        key={tag}
                        className='inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800'
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
