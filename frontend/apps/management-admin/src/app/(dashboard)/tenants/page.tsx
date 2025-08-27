'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  PlusIcon, 
  MagnifyingGlassIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useToast } from '@/components/ui/Toast';
import { tenantApi } from '@/lib/api';
import { Tenant, TenantStatus } from '@/types/tenant';

export default function TenantsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  // Fetch tenants
  const { data: tenantsData, isLoading, error: fetchError } = useQuery({
    queryKey: ['tenants', { page: currentPage, search: searchTerm, status: selectedStatus }],
    queryFn: () => tenantApi.list({
      page: currentPage,
      limit: 10,
      search: searchTerm || undefined,
      status: selectedStatus !== 'all' ? selectedStatus : undefined,
    }),
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

  const handleDeleteTenant = async (tenant: Tenant) => {
    if (window.confirm(`Are you sure you want to delete tenant "${tenant.name}"? This action cannot be undone.`)) {
      deleteTenantMutation.mutate(tenant.id);
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

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tenants</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage all tenant accounts and their configurations
          </p>
        </div>
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
      </div>

      {/* Filters */}
      <div className="card">
        <div className="card-content">
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
                  Showing {((currentPage - 1) * 10) + 1} to{' '}
                  {Math.min(currentPage * 10, tenantsData.total)} of{' '}
                  {tenantsData.total} results
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tenants Table */}
      <div className="card">
        <div className="overflow-hidden">
          {isLoading ? (
            <div className="flex justify-center items-center py-12">
              <LoadingSpinner size="large" />
            </div>
          ) : fetchError ? (
            <div className="text-center py-12">
              <p className="text-danger-600">Failed to load tenants</p>
            </div>
          ) : (
            <table className="table">
              <thead className="table-header">
                <tr>
                  <th className="table-header-cell">Name</th>
                  <th className="table-header-cell">Status</th>
                  <th className="table-header-cell">Plan</th>
                  <th className="table-header-cell">Contact</th>
                  <th className="table-header-cell">Created</th>
                  <th className="table-header-cell">Actions</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {tenantsData?.tenants?.map((tenant: Tenant) => (
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
                      <span className={getStatusBadge(tenant.status)}>
                        {tenant.status}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className="text-sm text-gray-900">
                        {tenant.plan || 'No Plan'}
                      </span>
                    </td>
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
        {tenantsData && tenantsData.pages > 1 && (
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
      </div>
    </div>
  );
}