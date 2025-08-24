'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useToast } from '@/components/ui/Toast';
import { tenantApi, billingApi } from '@/lib/api';
import { CreateTenantRequest } from '@/types/tenant';

interface CreateTenantForm extends CreateTenantRequest {
  confirmSlug: string;
}

export default function CreateTenantPage() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { success, error } = useToast();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<CreateTenantForm>();

  const tenantName = watch('name');

  // Auto-generate slug from tenant name
  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  };

  // Update slug when name changes
  React.useEffect(() => {
    if (tenantName) {
      const slug = generateSlug(tenantName);
      setValue('slug', slug);
      setValue('confirmSlug', slug);
    }
  }, [tenantName, setValue]);

  // Fetch billing plans
  const { data: billingPlans } = useQuery({
    queryKey: ['billing-plans'],
    queryFn: () => billingApi.plans.list(),
  });

  // Create tenant mutation
  const createTenantMutation = useMutation({
    mutationFn: tenantApi.create,
    onSuccess: (data) => {
      success('Tenant created successfully');
      router.push(`/tenants/${data.id}`);
    },
    onError: (error: any) => {
      console.error('Create tenant error:', error);
      error('Failed to create tenant', error.message);
    },
  });

  const onSubmit = async (data: CreateTenantForm) => {
    if (data.slug !== data.confirmSlug) {
      error('Slug confirmation does not match');
      return;
    }

    const { confirmSlug, ...tenantData } = data;
    
    try {
      setIsLoading(true);
      await createTenantMutation.mutateAsync(tenantData);
    } catch (err) {
      // Error handled in mutation
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center space-x-3">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Create New Tenant</h1>
          <p className="mt-1 text-sm text-gray-600">
            Set up a new tenant account with their basic information and settings
          </p>
        </div>
      </div>

      {/* Create Form */}
      <div className="card">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Basic Information</h2>
          </div>

          <div className="card-content space-y-6">
            {/* Tenant Name */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="label">
                  Tenant Name <span className="text-danger-500">*</span>
                </label>
                <input
                  type="text"
                  {...register('name', {
                    required: 'Tenant name is required',
                    minLength: {
                      value: 2,
                      message: 'Name must be at least 2 characters',
                    },
                  })}
                  className={`input ${errors.name ? 'input-error' : ''}`}
                  placeholder="Acme Corporation"
                />
                {errors.name && (
                  <p className="error-text">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="label">
                  Slug <span className="text-danger-500">*</span>
                </label>
                <input
                  type="text"
                  {...register('slug', {
                    required: 'Slug is required',
                    pattern: {
                      value: /^[a-z0-9-]+$/,
                      message: 'Slug can only contain lowercase letters, numbers, and hyphens',
                    },
                  })}
                  className={`input ${errors.slug ? 'input-error' : ''}`}
                  placeholder="acme-corporation"
                />
                {errors.slug && (
                  <p className="error-text">{errors.slug.message}</p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  Used in URLs and system identifiers
                </p>
              </div>
            </div>

            {/* Confirm Slug */}
            <div>
              <label className="label">
                Confirm Slug <span className="text-danger-500">*</span>
              </label>
              <input
                type="text"
                {...register('confirmSlug', {
                  required: 'Please confirm the slug',
                })}
                className={`input ${errors.confirmSlug ? 'input-error' : ''}`}
                placeholder="Re-type the slug to confirm"
              />
              {errors.confirmSlug && (
                <p className="error-text">{errors.confirmSlug.message}</p>
              )}
            </div>

            {/* Domain */}
            <div>
              <label className="label">Custom Domain (Optional)</label>
              <input
                type="text"
                {...register('domain')}
                className="input"
                placeholder="tenant.example.com"
              />
              <p className="mt-1 text-xs text-gray-500">
                Custom domain for this tenant's portal
              </p>
            </div>

            {/* Contact Information */}
            <div className="border-t pt-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Contact Information</h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                  <label className="label">
                    Billing Email <span className="text-danger-500">*</span>
                  </label>
                  <input
                    type="email"
                    {...register('billingEmail', {
                      required: 'Billing email is required',
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Please enter a valid email address',
                      },
                    })}
                    className={`input ${errors.billingEmail ? 'input-error' : ''}`}
                    placeholder="billing@acme.com"
                  />
                  {errors.billingEmail && (
                    <p className="error-text">{errors.billingEmail.message}</p>
                  )}
                </div>

                <div>
                  <label className="label">
                    Contact Email <span className="text-danger-500">*</span>
                  </label>
                  <input
                    type="email"
                    {...register('contactEmail', {
                      required: 'Contact email is required',
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Please enter a valid email address',
                      },
                    })}
                    className={`input ${errors.contactEmail ? 'input-error' : ''}`}
                    placeholder="admin@acme.com"
                  />
                  {errors.contactEmail && (
                    <p className="error-text">{errors.contactEmail.message}</p>
                  )}
                </div>
              </div>

              <div className="mt-4">
                <label className="label">Contact Phone</label>
                <input
                  type="tel"
                  {...register('contactPhone')}
                  className="input"
                  placeholder="+1 (555) 123-4567"
                />
              </div>
            </div>

            {/* Billing Plan */}
            <div className="border-t pt-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Billing Plan</h3>
              
              <div>
                <label className="label">Initial Plan (Optional)</label>
                <select
                  {...register('planId')}
                  className="input"
                >
                  <option value="">No plan (set up later)</option>
                  {billingPlans?.items?.map((plan: any) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.name} - ${plan.price}/{plan.billing_interval}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  You can set up billing plans after creating the tenant
                </p>
              </div>
            </div>

            {/* Description */}
            <div className="border-t pt-6">
              <label className="label">Description</label>
              <textarea
                {...register('description')}
                rows={3}
                className="input"
                placeholder="Brief description of the tenant and their business..."
              />
            </div>
          </div>

          {/* Form Actions */}
          <div className="card-content border-t bg-gray-50 flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => router.back()}
              className="btn-secondary"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || createTenantMutation.isPending}
              className="btn-primary"
            >
              {isLoading || createTenantMutation.isPending ? (
                <>
                  <LoadingSpinner size="small" color="white" className="mr-2" />
                  Creating...
                </>
              ) : (
                'Create Tenant'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}