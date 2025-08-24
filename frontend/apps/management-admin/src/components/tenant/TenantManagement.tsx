'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  UsersIcon,
  CreditCardIcon,
  ChartBarIcon,
  CloudIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useToast } from '@/components/ui/Toast';
import { tenantApi, billingApi, monitoringApi } from '@/lib/api';
import { Tenant, TenantStatus } from '@/types/tenant';

interface TenantManagementProps {
  showCreateButton?: boolean;
  showStats?: boolean;
  compact?: boolean;
}

export function TenantManagement({ 
  showCreateButton = true, 
  showStats = true, 
  compact = false 
}: TenantManagementProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  // Fetch tenants
  const { data: tenantsData, isLoading: tenantsLoading, error: fetchError } = useQuery({
    queryKey: ['tenants', { page: currentPage, search: searchTerm, status: selectedStatus }],
    queryFn: () => tenantApi.list({
      page: currentPage,
      limit: compact ? 5 : 10,
      search: searchTerm || undefined,
      status: selectedStatus !== 'all' ? selectedStatus : undefined,
    }),
  });

  // Fetch system health for stats
  const { data: healthData } = useQuery({
    queryKey: ['system-health'],
    queryFn: () => monitoringApi.health(),
    refetchInterval: 30000,
    enabled: showStats,
  });

  // Delete tenant mutation
  const deleteTenantMutation = useMutation({
    mutationFn: tenantApi.delete,
    onSuccess: () => {
      success('Tenant deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
    onError: (error: any) => {
      error('Failed to delete tenant', error.message);
    },
  });

  // Status update mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TenantStatus }) => 
      tenantApi.updateStatus(id, status),
    onSuccess: () => {
      success('Tenant status updated successfully');
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
    onError: (error: any) => {
      error('Failed to update tenant status', error.message);
    },
  });

  const handleDeleteTenant = async (tenant: Tenant) => {
    if (window.confirm(`Are you sure you want to delete tenant "${tenant.name}"? This action cannot be undone.`)) {
      deleteTenantMutation.mutate(tenant.id);
    }
  };

  const handleStatusUpdate = (tenant: Tenant, status: TenantStatus) => {
    if (status !== tenant.status) {
      updateStatusMutation.mutate({ id: tenant.id, status });
    }
  };

  const getStatusBadge = (status: TenantStatus) => {
    const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
    
    switch (status) {
      case TenantStatus.ACTIVE:
        return `${baseClasses} bg-success-100 text-success-800`;
      case TenantStatus.INACTIVE:
        return `${baseClasses} bg-gray-100 text-gray-800`;
      case TenantStatus.SUSPENDED:
        return `${baseClasses} bg-warning-100 text-warning-800`;
      case TenantStatus.TERMINATED:
        return `${baseClasses} bg-danger-100 text-danger-800`;
      case TenantStatus.PENDING:
        return `${baseClasses} bg-primary-100 text-primary-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  };

  // Stats cards configuration
  const stats = showStats ? [
    {
      name: 'Total Tenants',
      value: tenantsData?.total || 0,
      change: '+12%',
      changeType: 'positive',
      icon: UsersIcon,
      href: '/tenants',
    },
    {
      name: 'Active Tenants',
      value: tenantsData?.tenants?.filter(t => t.status === TenantStatus.ACTIVE).length || 0,
      change: '+5%',
      changeType: 'positive',
      icon: CheckCircleIcon,
      href: '/tenants?status=active',
    },
    {
      name: 'System Health',
      value: healthData?.overall_status === 'healthy' ? 'Healthy' : 'Issues',
      change: healthData?.overall_status === 'healthy' ? 'All systems operational' : 'Needs attention',
      changeType: healthData?.overall_status === 'healthy' ? 'positive' : 'negative',
      icon: healthData?.overall_status === 'healthy' ? CheckCircleIcon : ExclamationTriangleIcon,
      href: '/monitoring',
    },
    {
      name: 'Pending Setup',
      value: tenantsData?.tenants?.filter(t => t.status === TenantStatus.PENDING).length || 0,
      change: 'Require attention',
      changeType: tenantsData?.tenants?.some(t => t.status === TenantStatus.PENDING) ? 'negative' : 'neutral',
      icon: ExclamationTriangleIcon,
      href: '/tenants?status=pending',
    },
  ] : [];

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      {showStats && !compact && (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.name}
                className="card hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => window.location.href = item.href}
              >
                <div className="card-content">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <Icon className={`h-8 w-8 ${
                        item.changeType === 'positive' 
                          ? 'text-success-600' 
                          : item.changeType === 'negative'
                          ? 'text-danger-600'
                          : 'text-gray-600'
                      }`} />
                    </div>
                    <div className="ml-4 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">
                          {item.name}
                        </dt>
                        <dd className="text-lg font-medium text-gray-900">
                          {tenantsLoading ? (
                            <LoadingSpinner size="small" />
                          ) : (
                            item.value
                          )}
                        </dd>
                      </dl>
                    </div>
                  </div>
                  <div className="mt-2">
                    <div className={`text-sm ${
                      item.changeType === 'positive' 
                        ? 'text-success-600' 
                        : item.changeType === 'negative'
                        ? 'text-danger-600'
                        : 'text-gray-600'
                    }`}>
                      {item.change}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tenant Management Section */}
      <div className="card">
        {/* Header */}
        <div className="card-header">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-medium text-gray-900">
                {compact ? 'Recent Tenants' : 'Tenant Management'}
              </h2>
              {!compact && (
                <p className="mt-1 text-sm text-gray-600">
                  Manage all tenant accounts and their configurations
                </p>
              )}
            </div>
            {showCreateButton && (
              <div className="mt-4 sm:mt-0">
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => window.location.href = '/tenants/new'}
                >
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Create Tenant
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Filters */}
        {!compact && (
          <div className="card-content border-b">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Search */}
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search tenants..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input pl-10"
                />
              </div>

              {/* Status Filter */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="input"
              >
                <option value="all">All Statuses</option>
                <option value={TenantStatus.ACTIVE}>Active</option>
                <option value={TenantStatus.INACTIVE}>Inactive</option>
                <option value={TenantStatus.SUSPENDED}>Suspended</option>
                <option value={TenantStatus.TERMINATED}>Terminated</option>
                <option value={TenantStatus.PENDING}>Pending</option>
              </select>

              {/* Results count */}
              <div className="flex items-center text-sm text-gray-600">
                {tenantsData && (
                  <span>
                    Showing {tenantsData.tenants?.length || 0} of {tenantsData.total} results
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tenants Table */}
        <div className="overflow-hidden">
          {tenantsLoading ? (
            <div className="flex justify-center items-center py-12">
              <LoadingSpinner size="large" />
            </div>
          ) : fetchError ? (
            <div className="text-center py-12">
              <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-danger-600" />
              <p className="mt-2 text-danger-600">Failed to load tenants</p>
              <p className="text-sm text-gray-500">Please try again later</p>
            </div>
          ) : tenantsData?.tenants?.length === 0 ? (
            <div className="text-center py-12">
              <UsersIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No tenants found</h3>
              <p className="mt-1 text-sm text-gray-500">
                {searchTerm || selectedStatus !== 'all' 
                  ? 'Try adjusting your search or filters'
                  : 'Create your first tenant to get started'
                }
              </p>
              {showCreateButton && (!searchTerm && selectedStatus === 'all') && (
                <div className="mt-6">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => window.location.href = '/tenants/new'}
                  >
                    <PlusIcon className="h-4 w-4 mr-2" />
                    Create Your First Tenant
                  </button>
                </div>
              )}
            </div>
          ) : (
            <table className="table">
              <thead className="table-header">
                <tr>
                  <th className="table-header-cell">Name</th>
                  <th className="table-header-cell">Status</th>
                  {!compact && <th className="table-header-cell">Plan</th>}
                  {!compact && <th className="table-header-cell">Contact</th>}
                  <th className="table-header-cell">Created</th>
                  <th className="table-header-cell">Actions</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {tenantsData?.tenants?.map((tenant) => (
                  <tr key={tenant.id} className="hover:bg-gray-50">
                    <td className="table-cell">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {tenant.name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {tenant.slug}
                        </div>
                      </div>
                    </td>
                    <td className="table-cell">
                      <select
                        value={tenant.status}
                        onChange={(e) => handleStatusUpdate(tenant, e.target.value as TenantStatus)}
                        className="text-xs border-0 bg-transparent focus:ring-0"
                        disabled={updateStatusMutation.isPending}
                      >
                        <option value={TenantStatus.ACTIVE}>Active</option>
                        <option value={TenantStatus.INACTIVE}>Inactive</option>
                        <option value={TenantStatus.SUSPENDED}>Suspended</option>
                        <option value={TenantStatus.TERMINATED}>Terminated</option>
                        <option value={TenantStatus.PENDING}>Pending</option>
                      </select>
                    </td>
                    {!compact && (
                      <td className="table-cell">
                        <span className="text-sm text-gray-900">
                          {tenant.plan || 'No Plan'}
                        </span>
                      </td>
                    )}
                    {!compact && (
                      <td className="table-cell">
                        <div className="text-sm text-gray-900">
                          {tenant.contactEmail}
                        </div>
                        {tenant.contactPhone && (
                          <div className="text-sm text-gray-500">
                            {tenant.contactPhone}
                          </div>
                        )}
                      </td>
                    )}
                    <td className="table-cell">
                      <time className="text-sm text-gray-900">
                        {new Date(tenant.createdAt).toLocaleDateString()}
                      </time>
                    </td>
                    <td className="table-cell">
                      <div className="flex space-x-2">
                        <button
                          type="button"
                          className="text-primary-600 hover:text-primary-900"
                          title="View Details"
                          onClick={() => window.location.href = `/tenants/${tenant.id}`}
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          className="text-gray-600 hover:text-gray-900"
                          title="Edit"
                          onClick={() => window.location.href = `/tenants/${tenant.id}/edit`}
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          className="text-danger-600 hover:text-danger-900"
                          title="Delete"
                          onClick={() => handleDeleteTenant(tenant)}
                          disabled={deleteTenantMutation.isPending}
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {!compact && tenantsData && tenantsData.pages > 1 && (
          <div className="bg-white px-4 py-3 border-t border-gray-200 sm:px-6">
            <div className="flex justify-between items-center">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="btn-secondary"
                >
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage(Math.min(tenantsData.pages, currentPage + 1))}
                  disabled={currentPage === tenantsData.pages}
                  className="btn-secondary ml-3"
                >
                  Next
                </button>
              </div>
              
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Page <span className="font-medium">{currentPage}</span> of{' '}
                    <span className="font-medium">{tenantsData.pages}</span>
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="btn-secondary rounded-r-none"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setCurrentPage(Math.min(tenantsData.pages, currentPage + 1))}
                      disabled={currentPage === tenantsData.pages}
                      className="btn-secondary rounded-l-none -ml-px"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* View All Link for Compact Mode */}
        {compact && tenantsData && tenantsData.total > (tenantsData.tenants?.length || 0) && (
          <div className="card-content border-t text-center">
            <button
              onClick={() => window.location.href = '/tenants'}
              className="text-sm text-primary-600 hover:text-primary-900 font-medium"
            >
              View all {tenantsData.total} tenants →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}