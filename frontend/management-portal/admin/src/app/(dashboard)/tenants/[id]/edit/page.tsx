'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useToast } from '@/components/ui/Toast';
import { tenantApi, billingApi } from '@/lib/api';
import { UpdateTenantRequest, TenantStatus } from '@/types/tenant';

interface EditTenantForm extends UpdateTenantRequest {
  status: TenantStatus;
  allowUserRegistration: boolean;
  maxUsers: number;
  features: string[];
}

export default function EditTenantPage() {
  const params = useParams();
  const router = useRouter();
  const tenantId = params.id as string;
  const [isLoading, setIsLoading] = useState(false);
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  // Fetch tenant details
  const { data: tenant, isLoading: tenantLoading } = useQuery({
    queryKey: ['tenant', tenantId],
    queryFn: () => tenantApi.get(tenantId),
    enabled: !!tenantId,
  });

  // Fetch billing plans for the plan selector
  const { data: billingPlans } = useQuery({
    queryKey: ['billing-plans'],
    queryFn: () => billingApi.plans.list(),
  });

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<EditTenantForm>();

  // Initialize form with tenant data
  React.useEffect(() => {
    if (tenant) {
      setValue('name', tenant.name);
      setValue('slug', tenant.slug);
      setValue('domain', tenant.domain || '');
      setValue('contactEmail', tenant.contactEmail || '');
      setValue('billingEmail', tenant.billingEmail || '');
      setValue('contactPhone', tenant.contactPhone || '');
      setValue('description', tenant.description || '');
      setValue('status', tenant.status);
      setValue('allowUserRegistration', tenant.settings?.allowUserRegistration || false);
      setValue('maxUsers', tenant.settings?.maxUsers || 0);
      setValue('features', tenant.settings?.features || []);
    }
  }, [tenant, setValue]);

  // Update tenant mutation
  const updateTenantMutation = useMutation({
    mutationFn: (data: UpdateTenantRequest) => tenantApi.update(tenantId, data),
    onSuccess: () => {
      success('Tenant updated successfully');
      queryClient.invalidateQueries({ queryKey: ['tenant', tenantId] });
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      router.push(`/tenants/${tenantId}`);
    },
    onError: (error: any) => {
      error('Failed to update tenant', error.message);
    },
  });

  const onSubmit = async (data: EditTenantForm) => {
    try {
      setIsLoading(true);

      // Separate status update from other updates
      const { status, allowUserRegistration, maxUsers, features, ...updateData } = data;

      // Include settings in update data
      const tenantUpdate: UpdateTenantRequest = {
        ...updateData,
        settings: {
          allowUserRegistration,
          maxUsers,
          features,
          customization: tenant?.settings?.customization || {},
          limits: tenant?.settings?.limits || { storage: 0, bandwidth: 0, apiCalls: 0 },
          integrations: tenant?.settings?.integrations || {},
        },
      };

      await updateTenantMutation.mutateAsync(tenantUpdate);

      // Update status separately if changed
      if (status !== tenant?.status) {
        await tenantApi.updateStatus(tenantId, status);
      }
    } catch (err) {
      // Error handled in mutation
    } finally {
      setIsLoading(false);
    }
  };

  if (tenantLoading) {
    return (
      <div className='flex justify-center items-center min-h-screen'>
        <LoadingSpinner size='large' />
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className='text-center py-12'>
        <h3 className='text-sm font-medium text-gray-900'>Tenant not found</h3>
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      {/* Page Header */}
      <div className='flex items-center space-x-3'>
        <button
          onClick={() => router.back()}
          className='inline-flex items-center text-sm text-gray-500 hover:text-gray-700'
        >
          <ArrowLeftIcon className='h-4 w-4 mr-1' />
          Back
        </button>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Edit Tenant: {tenant.name}</h1>
          <p className='mt-1 text-sm text-gray-600'>Update tenant information and settings</p>
        </div>
      </div>

      {/* Edit Form */}
      <div className='card'>
        <form onSubmit={handleSubmit(onSubmit)} className='space-y-6'>
          <div className='card-header'>
            <h2 className='text-lg font-medium text-gray-900'>Basic Information</h2>
          </div>

          <div className='card-content space-y-6'>
            {/* Tenant Name & Slug */}
            <div className='grid grid-cols-1 sm:grid-cols-2 gap-6'>
              <div>
                <label className='label'>
                  Tenant Name <span className='text-danger-500'>*</span>
                </label>
                <input
                  type='text'
                  {...register('name', {
                    required: 'Tenant name is required',
                    minLength: {
                      value: 2,
                      message: 'Name must be at least 2 characters',
                    },
                  })}
                  className={`input ${errors.name ? 'input-error' : ''}`}
                />
                {errors.name && <p className='error-text'>{errors.name.message}</p>}
              </div>

              <div>
                <label className='label'>
                  Slug <span className='text-danger-500'>*</span>
                </label>
                <input
                  type='text'
                  {...register('slug', {
                    required: 'Slug is required',
                    pattern: {
                      value: /^[a-z0-9-]+$/,
                      message: 'Slug can only contain lowercase letters, numbers, and hyphens',
                    },
                  })}
                  className={`input ${errors.slug ? 'input-error' : ''}`}
                />
                {errors.slug && <p className='error-text'>{errors.slug.message}</p>}
                <p className='mt-1 text-xs text-gray-500'>Used in URLs and system identifiers</p>
              </div>
            </div>

            {/* Status & Domain */}
            <div className='grid grid-cols-1 sm:grid-cols-2 gap-6'>
              <div>
                <label className='label'>Status</label>
                <select {...register('status')} className='input'>
                  <option value={TenantStatus.ACTIVE}>Active</option>
                  <option value={TenantStatus.INACTIVE}>Inactive</option>
                  <option value={TenantStatus.SUSPENDED}>Suspended</option>
                  <option value={TenantStatus.TERMINATED}>Terminated</option>
                  <option value={TenantStatus.PENDING}>Pending</option>
                </select>
              </div>

              <div>
                <label className='label'>Custom Domain</label>
                <input
                  type='text'
                  {...register('domain')}
                  className='input'
                  placeholder='tenant.example.com'
                />
                <p className='mt-1 text-xs text-gray-500'>Custom domain for this tenant's portal</p>
              </div>
            </div>

            {/* Contact Information */}
            <div className='border-t pt-6'>
              <h3 className='text-lg font-medium text-gray-900 mb-4'>Contact Information</h3>

              <div className='grid grid-cols-1 sm:grid-cols-2 gap-6'>
                <div>
                  <label className='label'>
                    Contact Email <span className='text-danger-500'>*</span>
                  </label>
                  <input
                    type='email'
                    {...register('contactEmail', {
                      required: 'Contact email is required',
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Please enter a valid email address',
                      },
                    })}
                    className={`input ${errors.contactEmail ? 'input-error' : ''}`}
                  />
                  {errors.contactEmail && (
                    <p className='error-text'>{errors.contactEmail.message}</p>
                  )}
                </div>

                <div>
                  <label className='label'>Billing Email</label>
                  <input
                    type='email'
                    {...register('billingEmail', {
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Please enter a valid email address',
                      },
                    })}
                    className={`input ${errors.billingEmail ? 'input-error' : ''}`}
                  />
                  {errors.billingEmail && (
                    <p className='error-text'>{errors.billingEmail.message}</p>
                  )}
                </div>
              </div>

              <div className='mt-4'>
                <label className='label'>Contact Phone</label>
                <input
                  type='tel'
                  {...register('contactPhone')}
                  className='input'
                  placeholder='+1 (555) 123-4567'
                />
              </div>
            </div>

            {/* Tenant Settings */}
            <div className='border-t pt-6'>
              <h3 className='text-lg font-medium text-gray-900 mb-4'>Settings</h3>

              <div className='space-y-4'>
                <div className='flex items-center'>
                  <input
                    id='allowUserRegistration'
                    type='checkbox'
                    {...register('allowUserRegistration')}
                    className='h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
                  />
                  <label
                    htmlFor='allowUserRegistration'
                    className='ml-2 block text-sm text-gray-900'
                  >
                    Allow user registration
                  </label>
                </div>

                <div>
                  <label className='label'>Maximum Users</label>
                  <input
                    type='number'
                    {...register('maxUsers', {
                      min: { value: 0, message: 'Must be 0 or greater' },
                    })}
                    className={`input ${errors.maxUsers ? 'input-error' : ''}`}
                    placeholder='0 for unlimited'
                  />
                  {errors.maxUsers && <p className='error-text'>{errors.maxUsers.message}</p>}
                  <p className='mt-1 text-xs text-gray-500'>Set to 0 for unlimited users</p>
                </div>
              </div>
            </div>

            {/* Description */}
            <div className='border-t pt-6'>
              <label className='label'>Description</label>
              <textarea
                {...register('description')}
                rows={3}
                className='input'
                placeholder='Brief description of the tenant and their business...'
              />
            </div>
          </div>

          {/* Form Actions */}
          <div className='card-content border-t bg-gray-50 flex justify-end space-x-3'>
            <button
              type='button'
              onClick={() => router.back()}
              className='btn-secondary'
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type='submit'
              disabled={isLoading || updateTenantMutation.isPending}
              className='btn-primary'
            >
              {isLoading || updateTenantMutation.isPending ? (
                <>
                  <LoadingSpinner size='small' color='white' className='mr-2' />
                  Updating...
                </>
              ) : (
                'Update Tenant'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
