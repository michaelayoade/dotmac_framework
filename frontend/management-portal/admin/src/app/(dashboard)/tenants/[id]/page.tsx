'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  PencilIcon,
  TrashIcon,
  UsersIcon,
  CreditCardIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useToast } from '@/components/ui/Toast';
import { tenantApi, billingApi } from '@/lib/api';
import { Tenant, TenantStatus } from '@/types/tenant';

export default function TenantDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const tenantId = params.id as string;
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  // Fetch tenant details
  const {
    data: tenant,
    isLoading: tenantLoading,
    error: tenantError,
  } = useQuery({
    queryKey: ['tenant', tenantId],
    queryFn: () => tenantApi.get(tenantId),
    enabled: !!tenantId,
  });

  // Fetch tenant subscriptions
  const { data: subscriptions, isLoading: subscriptionsLoading } = useQuery({
    queryKey: ['tenant-subscriptions', tenantId],
    queryFn: () => billingApi.subscriptions.list({ tenant_id: tenantId }),
    enabled: !!tenantId,
  });

  // Status update mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ status }: { status: TenantStatus }) => tenantApi.updateStatus(tenantId, status),
    onSuccess: () => {
      success('Tenant status updated successfully');
      queryClient.invalidateQueries({ queryKey: ['tenant', tenantId] });
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
    onError: (error: any) => {
      error('Failed to update tenant status', error.message);
    },
  });

  // Delete tenant mutation
  const deleteTenantMutation = useMutation({
    mutationFn: () => tenantApi.delete(tenantId),
    onSuccess: () => {
      success('Tenant deleted successfully');
      router.push('/tenants');
    },
    onError: (error: any) => {
      error('Failed to delete tenant', error.message);
    },
  });

  const handleStatusUpdate = (status: TenantStatus) => {
    if (window.confirm(`Are you sure you want to change the status to ${status}?`)) {
      updateStatusMutation.mutate({ status });
    }
  };

  const handleDeleteTenant = () => {
    if (
      window.confirm(
        `Are you sure you want to delete "${tenant?.name}"? This action cannot be undone.`
      )
    ) {
      deleteTenantMutation.mutate();
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

  if (tenantLoading) {
    return (
      <div className='flex justify-center items-center min-h-screen'>
        <LoadingSpinner size='large' />
      </div>
    );
  }

  if (tenantError) {
    return (
      <div className='text-center py-12'>
        <ExclamationTriangleIcon className='mx-auto h-12 w-12 text-danger-600' />
        <h3 className='mt-2 text-sm font-medium text-gray-900'>Failed to load tenant</h3>
        <p className='mt-1 text-sm text-gray-500'>Please try again later</p>
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className='text-center py-12'>
        <ExclamationTriangleIcon className='mx-auto h-12 w-12 text-gray-400' />
        <h3 className='mt-2 text-sm font-medium text-gray-900'>Tenant not found</h3>
        <p className='mt-1 text-sm text-gray-500'>The requested tenant could not be found</p>
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      {/* Page Header */}
      <div className='flex items-center justify-between'>
        <div className='flex items-center space-x-3'>
          <button
            onClick={() => router.back()}
            className='inline-flex items-center text-sm text-gray-500 hover:text-gray-700'
          >
            <ArrowLeftIcon className='h-4 w-4 mr-1' />
            Back
          </button>
          <div>
            <div className='flex items-center space-x-3'>
              <h1 className='text-2xl font-bold text-gray-900'>{tenant.name}</h1>
              <span className={getStatusBadge(tenant.status)}>{tenant.status}</span>
            </div>
            <p className='mt-1 text-sm text-gray-600'>
              {tenant.slug} {tenant.domain && `• ${tenant.domain}`}
            </p>
          </div>
        </div>

        <div className='flex items-center space-x-3'>
          {/* Status Actions */}
          <div className='relative'>
            <select
              onChange={(e) => handleStatusUpdate(e.target.value as TenantStatus)}
              value={tenant.status}
              className='input text-sm'
              disabled={updateStatusMutation.isPending}
            >
              <option value={TenantStatus.ACTIVE}>Active</option>
              <option value={TenantStatus.INACTIVE}>Inactive</option>
              <option value={TenantStatus.SUSPENDED}>Suspended</option>
              <option value={TenantStatus.TERMINATED}>Terminated</option>
              <option value={TenantStatus.PENDING}>Pending</option>
            </select>
          </div>

          <button
            onClick={() => router.push(`/tenants/${tenantId}/edit`)}
            className='btn-secondary'
          >
            <PencilIcon className='h-4 w-4 mr-2' />
            Edit
          </button>

          <button
            onClick={handleDeleteTenant}
            disabled={deleteTenantMutation.isPending}
            className='btn-danger'
          >
            <TrashIcon className='h-4 w-4 mr-2' />
            Delete
          </button>
        </div>
      </div>

      {/* Tenant Overview Cards */}
      <div className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6'>
        <div className='card'>
          <div className='card-content'>
            <div className='flex items-center'>
              <UsersIcon className='h-8 w-8 text-primary-600' />
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Users</p>
                <p className='text-2xl font-semibold text-gray-900'>
                  {tenant.settings?.maxUsers || 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className='card'>
          <div className='card-content'>
            <div className='flex items-center'>
              <CreditCardIcon className='h-8 w-8 text-success-600' />
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Plan</p>
                <p className='text-2xl font-semibold text-gray-900'>{tenant.plan || 'None'}</p>
              </div>
            </div>
          </div>
        </div>

        <div className='card'>
          <div className='card-content'>
            <div className='flex items-center'>
              <ChartBarIcon className='h-8 w-8 text-warning-600' />
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Storage</p>
                <p className='text-2xl font-semibold text-gray-900'>
                  {tenant.settings?.limits?.storage
                    ? `${(tenant.settings.limits.storage / 1024 / 1024 / 1024).toFixed(1)}GB`
                    : 'Unlimited'}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className='card'>
          <div className='card-content'>
            <div className='flex items-center'>
              <CheckCircleIcon className='h-8 w-8 text-info-600' />
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Created</p>
                <p className='text-2xl font-semibold text-gray-900'>
                  {new Date(tenant.createdAt).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Tenant Information */}
        <div className='card'>
          <div className='card-header'>
            <h3 className='text-lg font-medium text-gray-900'>Tenant Information</h3>
          </div>
          <div className='card-content'>
            <dl className='space-y-4'>
              <div>
                <dt className='text-sm font-medium text-gray-500'>Name</dt>
                <dd className='mt-1 text-sm text-gray-900'>{tenant.name}</dd>
              </div>
              <div>
                <dt className='text-sm font-medium text-gray-500'>Slug</dt>
                <dd className='mt-1 text-sm text-gray-900'>{tenant.slug}</dd>
              </div>
              {tenant.domain && (
                <div>
                  <dt className='text-sm font-medium text-gray-500'>Domain</dt>
                  <dd className='mt-1 text-sm text-gray-900'>
                    <a
                      href={`https://${tenant.domain}`}
                      target='_blank'
                      rel='noopener noreferrer'
                      className='text-primary-600 hover:text-primary-900'
                    >
                      {tenant.domain}
                    </a>
                  </dd>
                </div>
              )}
              <div>
                <dt className='text-sm font-medium text-gray-500'>Contact Email</dt>
                <dd className='mt-1 text-sm text-gray-900'>
                  <a
                    href={`mailto:${tenant.contactEmail}`}
                    className='text-primary-600 hover:text-primary-900'
                  >
                    {tenant.contactEmail}
                  </a>
                </dd>
              </div>
              {tenant.billingEmail && tenant.billingEmail !== tenant.contactEmail && (
                <div>
                  <dt className='text-sm font-medium text-gray-500'>Billing Email</dt>
                  <dd className='mt-1 text-sm text-gray-900'>
                    <a
                      href={`mailto:${tenant.billingEmail}`}
                      className='text-primary-600 hover:text-primary-900'
                    >
                      {tenant.billingEmail}
                    </a>
                  </dd>
                </div>
              )}
              {tenant.contactPhone && (
                <div>
                  <dt className='text-sm font-medium text-gray-500'>Phone</dt>
                  <dd className='mt-1 text-sm text-gray-900'>{tenant.contactPhone}</dd>
                </div>
              )}
              {tenant.description && (
                <div>
                  <dt className='text-sm font-medium text-gray-500'>Description</dt>
                  <dd className='mt-1 text-sm text-gray-900'>{tenant.description}</dd>
                </div>
              )}
              <div>
                <dt className='text-sm font-medium text-gray-500'>Last Activity</dt>
                <dd className='mt-1 text-sm text-gray-900'>
                  {tenant.lastActivity
                    ? new Date(tenant.lastActivity).toLocaleString()
                    : 'No recent activity'}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Subscription Information */}
        <div className='card'>
          <div className='card-header'>
            <h3 className='text-lg font-medium text-gray-900'>Subscriptions</h3>
          </div>
          <div className='card-content'>
            {subscriptionsLoading ? (
              <div className='flex justify-center py-4'>
                <LoadingSpinner />
              </div>
            ) : subscriptions && subscriptions.length > 0 ? (
              <div className='space-y-4'>
                {subscriptions.map((subscription: any) => (
                  <div key={subscription.id} className='border rounded-lg p-4'>
                    <div className='flex justify-between items-start'>
                      <div>
                        <h4 className='text-sm font-medium text-gray-900'>
                          {subscription.plan_name}
                        </h4>
                        <p className='text-sm text-gray-500'>
                          ${subscription.amount}/{subscription.billing_interval}
                        </p>
                      </div>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          subscription.status === 'active'
                            ? 'bg-success-100 text-success-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {subscription.status}
                      </span>
                    </div>
                    <div className='mt-2 text-xs text-gray-500'>
                      Started: {new Date(subscription.created_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className='text-center py-4'>
                <CreditCardIcon className='mx-auto h-8 w-8 text-gray-400' />
                <p className='text-sm text-gray-500'>No active subscriptions</p>
                <button
                  className='mt-2 btn-primary btn-sm'
                  onClick={() => router.push(`/tenants/${tenantId}/subscriptions/new`)}
                >
                  Create Subscription
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Settings Overview */}
      <div className='card'>
        <div className='card-header'>
          <div className='flex justify-between items-center'>
            <h3 className='text-lg font-medium text-gray-900'>Settings & Features</h3>
            <button
              onClick={() => router.push(`/tenants/${tenantId}/settings`)}
              className='btn-secondary btn-sm'
            >
              <Cog6ToothIcon className='h-4 w-4 mr-2' />
              Manage Settings
            </button>
          </div>
        </div>
        <div className='card-content'>
          <div className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6'>
            <div>
              <dt className='text-sm font-medium text-gray-500'>User Registration</dt>
              <dd className='mt-1 text-sm text-gray-900'>
                {tenant.settings?.allowUserRegistration ? 'Enabled' : 'Disabled'}
              </dd>
            </div>
            <div>
              <dt className='text-sm font-medium text-gray-500'>Max Users</dt>
              <dd className='mt-1 text-sm text-gray-900'>
                {tenant.settings?.maxUsers || 'Unlimited'}
              </dd>
            </div>
            <div>
              <dt className='text-sm font-medium text-gray-500'>Features</dt>
              <dd className='mt-1 text-sm text-gray-900'>
                {tenant.settings?.features?.length || 0} enabled
              </dd>
            </div>
            {tenant.settings?.limits && (
              <>
                <div>
                  <dt className='text-sm font-medium text-gray-500'>Bandwidth Limit</dt>
                  <dd className='mt-1 text-sm text-gray-900'>
                    {tenant.settings.limits.bandwidth
                      ? `${(tenant.settings.limits.bandwidth / 1024 / 1024).toFixed(0)}MB`
                      : 'Unlimited'}
                  </dd>
                </div>
                <div>
                  <dt className='text-sm font-medium text-gray-500'>API Calls Limit</dt>
                  <dd className='mt-1 text-sm text-gray-900'>
                    {tenant.settings.limits.apiCalls
                      ? tenant.settings.limits.apiCalls.toLocaleString()
                      : 'Unlimited'}
                  </dd>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
