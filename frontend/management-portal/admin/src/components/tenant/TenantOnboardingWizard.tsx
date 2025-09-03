/**
 * Tenant Onboarding Wizard Component
 * Multi-step guided setup for new tenants
 * Connects to existing tenant provisioning and auto-license APIs
 */

import React, { useState } from 'react';
import {
  CheckIcon,
  XMarkIcon,
  ArrowRightIcon,
  ArrowLeftIcon,
  BuildingOfficeIcon,
  UserGroupIcon,
  CogIcon,
  CloudIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/http';
import { useToast } from '@/components/ui/Toast';

interface TenantOnboardingData {
  // Basic Information
  companyName: string;
  contactEmail: string;
  contactPhone: string;
  industry: string;
  companySize: string;

  // Technical Configuration
  subdomain: string;
  timezone: string;
  currency: string;
  language: string;

  // Applications & Features
  selectedApps: string[];
  features: {
    multiFactorAuth: boolean;
    ssoEnabled: boolean;
    auditLogging: boolean;
    apiAccess: boolean;
    customBranding: boolean;
  };

  // Infrastructure
  deploymentRegion: string;
  storageQuota: number;
  bandwidthLimit: number;
  userLimit: number;

  // Billing
  billingPlan: string;
  billingCycle: 'monthly' | 'yearly';
  paymentMethod: string;
}

interface TenantOnboardingWizardProps {
  onComplete: (tenantId: string) => void;
  onCancel: () => void;
}

const STEPS = [
  { id: 'basic', title: 'Basic Information', icon: BuildingOfficeIcon },
  { id: 'technical', title: 'Technical Setup', icon: CogIcon },
  { id: 'applications', title: 'Applications & Features', icon: UserGroupIcon },
  { id: 'infrastructure', title: 'Infrastructure', icon: CloudIcon },
  { id: 'review', title: 'Review & Deploy', icon: CheckCircleIcon },
];

const AVAILABLE_APPS = [
  {
    id: 'isp_framework',
    name: 'ISP Framework',
    description: 'Core ISP management tools',
    required: true,
  },
  { id: 'crm', name: 'Customer CRM', description: 'Customer relationship management' },
  { id: 'billing', name: 'Billing System', description: 'Advanced billing and invoicing' },
  { id: 'support', name: 'Support Portal', description: 'Customer support system' },
  { id: 'analytics', name: 'Business Analytics', description: 'Reporting and analytics dashboard' },
  { id: 'e_commerce', name: 'E-Commerce', description: 'Online store and product catalog' },
];

const BILLING_PLANS = [
  { id: 'starter', name: 'Starter', price: 99, description: 'Perfect for small businesses' },
  { id: 'professional', name: 'Professional', price: 299, description: 'Growing businesses' },
  { id: 'enterprise', name: 'Enterprise', price: 999, description: 'Large organizations' },
];

export function TenantOnboardingWizard({ onComplete, onCancel }: TenantOnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [onboardingData, setOnboardingData] = useState<TenantOnboardingData>({
    companyName: '',
    contactEmail: '',
    contactPhone: '',
    industry: '',
    companySize: '',
    subdomain: '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    currency: 'USD',
    language: 'en',
    selectedApps: ['isp_framework'],
    features: {
      multiFactorAuth: true,
      ssoEnabled: false,
      auditLogging: true,
      apiAccess: false,
      customBranding: false,
    },
    deploymentRegion: 'us-east-1',
    storageQuota: 10,
    bandwidthLimit: 100,
    userLimit: 25,
    billingPlan: 'professional',
    billingCycle: 'monthly',
    paymentMethod: '',
  });

  const { success, error } = useToast();

  // Tenant creation mutation
  const createTenantMutation = useMutation({
    mutationFn: async (data: TenantOnboardingData) => {
      const res = await api.post<{ tenant_id: string }>(
        '/api/v1/tenants/onboard',
        data
      );
      return res.data;
    },
    onSuccess: (data) => {
      success('Tenant created successfully! Provisioning infrastructure...');
      onComplete(data.tenant_id);
    },
    onError: (err: any) => {
      error('Failed to create tenant', err.message);
    },
  });

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = () => {
    createTenantMutation.mutate(onboardingData);
  };

  const isStepComplete = (stepIndex: number): boolean => {
    switch (stepIndex) {
      case 0: // Basic
        return !!(
          onboardingData.companyName &&
          onboardingData.contactEmail &&
          onboardingData.industry
        );
      case 1: // Technical
        return !!(onboardingData.subdomain && onboardingData.timezone);
      case 2: // Applications
        return onboardingData.selectedApps.length > 0;
      case 3: // Infrastructure
        return !!(onboardingData.deploymentRegion && onboardingData.billingPlan);
      case 4: // Review
        return true;
      default:
        return false;
    }
  };

  const canProceed = isStepComplete(currentStep);

  const renderStepContent = () => {
    switch (STEPS[currentStep].id) {
      case 'basic':
        return (
          <div className='space-y-6'>
            <div>
              <h3 className='text-lg font-medium text-gray-900 mb-4'>Company Information</h3>

              <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Company Name *
                  </label>
                  <input
                    type='text'
                    value={onboardingData.companyName}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({ ...prev, companyName: e.target.value }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                    placeholder='Enter company name'
                  />
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>Industry *</label>
                  <select
                    value={onboardingData.industry}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({ ...prev, industry: e.target.value }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                  >
                    <option value=''>Select industry</option>
                    <option value='telecommunications'>Telecommunications</option>
                    <option value='internet_service'>Internet Service Provider</option>
                    <option value='technology'>Technology</option>
                    <option value='healthcare'>Healthcare</option>
                    <option value='finance'>Finance</option>
                    <option value='education'>Education</option>
                    <option value='government'>Government</option>
                    <option value='other'>Other</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Contact Email *
                  </label>
                  <input
                    type='email'
                    value={onboardingData.contactEmail}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({ ...prev, contactEmail: e.target.value }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                    placeholder='admin@company.com'
                  />
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Contact Phone
                  </label>
                  <input
                    type='tel'
                    value={onboardingData.contactPhone}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({ ...prev, contactPhone: e.target.value }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                    placeholder='+1 (555) 123-4567'
                  />
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Company Size
                  </label>
                  <select
                    value={onboardingData.companySize}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({ ...prev, companySize: e.target.value }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                  >
                    <option value=''>Select size</option>
                    <option value='1-10'>1-10 employees</option>
                    <option value='11-50'>11-50 employees</option>
                    <option value='51-200'>51-200 employees</option>
                    <option value='201-1000'>201-1000 employees</option>
                    <option value='1000+'>1000+ employees</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        );

      case 'technical':
        return (
          <div className='space-y-6'>
            <div>
              <h3 className='text-lg font-medium text-gray-900 mb-4'>Technical Configuration</h3>

              <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Subdomain *
                  </label>
                  <div className='flex'>
                    <input
                      type='text'
                      value={onboardingData.subdomain}
                      onChange={(e) =>
                        setOnboardingData((prev) => ({
                          ...prev,
                          subdomain: e.target.value.toLowerCase(),
                        }))
                      }
                      className='flex-1 px-3 py-2 border border-gray-300 rounded-l-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                      placeholder='company'
                    />
                    <span className='inline-flex items-center px-3 py-2 border border-l-0 border-gray-300 bg-gray-50 text-gray-500 text-sm rounded-r-md'>
                      .dotmac.app
                    </span>
                  </div>
                  <p className='mt-1 text-sm text-gray-500'>
                    This will be your tenant's URL: https://{onboardingData.subdomain || 'company'}
                    .dotmac.app
                  </p>
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>Timezone *</label>
                  <select
                    value={onboardingData.timezone}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({ ...prev, timezone: e.target.value }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                  >
                    <option value='America/New_York'>Eastern Time (ET)</option>
                    <option value='America/Chicago'>Central Time (CT)</option>
                    <option value='America/Denver'>Mountain Time (MT)</option>
                    <option value='America/Los_Angeles'>Pacific Time (PT)</option>
                    <option value='Europe/London'>London (GMT)</option>
                    <option value='Europe/Paris'>Paris (CET)</option>
                    <option value='Asia/Tokyo'>Tokyo (JST)</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>Currency</label>
                  <select
                    value={onboardingData.currency}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({ ...prev, currency: e.target.value }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                  >
                    <option value='USD'>US Dollar (USD)</option>
                    <option value='EUR'>Euro (EUR)</option>
                    <option value='GBP'>British Pound (GBP)</option>
                    <option value='CAD'>Canadian Dollar (CAD)</option>
                    <option value='AUD'>Australian Dollar (AUD)</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Primary Language
                  </label>
                  <select
                    value={onboardingData.language}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({ ...prev, language: e.target.value }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                  >
                    <option value='en'>English</option>
                    <option value='es'>Spanish</option>
                    <option value='fr'>French</option>
                    <option value='de'>German</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        );

      case 'applications':
        return (
          <div className='space-y-6'>
            <div>
              <h3 className='text-lg font-medium text-gray-900 mb-4'>Applications & Features</h3>

              <div className='space-y-4 mb-8'>
                <h4 className='font-medium text-gray-900'>Select Applications</h4>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                  {AVAILABLE_APPS.map((app) => {
                    const isSelected = onboardingData.selectedApps.includes(app.id);
                    return (
                      <div
                        key={app.id}
                        className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                          isSelected
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-300 hover:border-gray-400'
                        } ${app.required ? 'opacity-50 cursor-not-allowed' : ''}`}
                        onClick={() => {
                          if (app.required) return;
                          setOnboardingData((prev) => ({
                            ...prev,
                            selectedApps: isSelected
                              ? prev.selectedApps.filter((id) => id !== app.id)
                              : [...prev.selectedApps, app.id],
                          }));
                        }}
                      >
                        <div className='flex items-center justify-between'>
                          <div className='flex-1'>
                            <h5 className='font-medium text-gray-900'>{app.name}</h5>
                            <p className='text-sm text-gray-600'>{app.description}</p>
                            {app.required && (
                              <span className='inline-block mt-1 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded'>
                                Required
                              </span>
                            )}
                          </div>
                          {isSelected && <CheckIcon className='h-5 w-5 text-blue-600' />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className='space-y-4'>
                <h4 className='font-medium text-gray-900'>Additional Features</h4>
                <div className='space-y-3'>
                  {Object.entries(onboardingData.features).map(([key, value]) => (
                    <label key={key} className='flex items-center'>
                      <input
                        type='checkbox'
                        checked={value}
                        onChange={(e) =>
                          setOnboardingData((prev) => ({
                            ...prev,
                            features: { ...prev.features, [key]: e.target.checked },
                          }))
                        }
                        className='rounded border-gray-300 text-blue-600 focus:ring-blue-500'
                      />
                      <span className='ml-2 text-sm text-gray-700'>
                        {key === 'multiFactorAuth' && 'Multi-Factor Authentication'}
                        {key === 'ssoEnabled' && 'Single Sign-On (SSO)'}
                        {key === 'auditLogging' && 'Advanced Audit Logging'}
                        {key === 'apiAccess' && 'API Access'}
                        {key === 'customBranding' && 'Custom Branding'}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        );

      case 'infrastructure':
        return (
          <div className='space-y-6'>
            <div>
              <h3 className='text-lg font-medium text-gray-900 mb-4'>Infrastructure & Billing</h3>

              <div className='grid grid-cols-1 md:grid-cols-2 gap-6 mb-8'>
                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Deployment Region
                  </label>
                  <select
                    value={onboardingData.deploymentRegion}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({ ...prev, deploymentRegion: e.target.value }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                  >
                    <option value='us-east-1'>US East (Virginia)</option>
                    <option value='us-west-2'>US West (Oregon)</option>
                    <option value='eu-west-1'>Europe (Ireland)</option>
                    <option value='ap-southeast-1'>Asia Pacific (Singapore)</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>User Limit</label>
                  <select
                    value={onboardingData.userLimit}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({
                        ...prev,
                        userLimit: parseInt(e.target.value),
                      }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                  >
                    <option value={25}>25 users</option>
                    <option value={100}>100 users</option>
                    <option value={500}>500 users</option>
                    <option value={1000}>1000 users</option>
                    <option value={0}>Unlimited</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Storage Quota (GB)
                  </label>
                  <select
                    value={onboardingData.storageQuota}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({
                        ...prev,
                        storageQuota: parseInt(e.target.value),
                      }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                  >
                    <option value={10}>10 GB</option>
                    <option value={50}>50 GB</option>
                    <option value={100}>100 GB</option>
                    <option value={500}>500 GB</option>
                    <option value={1000}>1 TB</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    Bandwidth Limit (GB/month)
                  </label>
                  <select
                    value={onboardingData.bandwidthLimit}
                    onChange={(e) =>
                      setOnboardingData((prev) => ({
                        ...prev,
                        bandwidthLimit: parseInt(e.target.value),
                      }))
                    }
                    className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                  >
                    <option value={100}>100 GB</option>
                    <option value={500}>500 GB</option>
                    <option value={1000}>1 TB</option>
                    <option value={5000}>5 TB</option>
                    <option value={0}>Unlimited</option>
                  </select>
                </div>
              </div>

              <div>
                <h4 className='font-medium text-gray-900 mb-4'>Billing Plan</h4>
                <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
                  {BILLING_PLANS.map((plan) => {
                    const isSelected = onboardingData.billingPlan === plan.id;
                    return (
                      <div
                        key={plan.id}
                        className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                          isSelected
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-300 hover:border-gray-400'
                        }`}
                        onClick={() =>
                          setOnboardingData((prev) => ({ ...prev, billingPlan: plan.id }))
                        }
                      >
                        <div className='text-center'>
                          <h5 className='font-medium text-gray-900'>{plan.name}</h5>
                          <p className='text-2xl font-bold text-gray-900 my-2'>
                            ${plan.price}
                            <span className='text-sm font-normal'>/month</span>
                          </p>
                          <p className='text-sm text-gray-600'>{plan.description}</p>
                          {isSelected && (
                            <CheckIcon className='h-5 w-5 text-blue-600 mx-auto mt-2' />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className='mt-4'>
                  <label className='flex items-center'>
                    <input
                      type='radio'
                      name='billingCycle'
                      value='monthly'
                      checked={onboardingData.billingCycle === 'monthly'}
                      onChange={(e) =>
                        setOnboardingData((prev) => ({ ...prev, billingCycle: 'monthly' as const }))
                      }
                      className='focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300'
                    />
                    <span className='ml-2 text-sm text-gray-700'>Monthly billing</span>
                  </label>
                  <label className='flex items-center mt-2'>
                    <input
                      type='radio'
                      name='billingCycle'
                      value='yearly'
                      checked={onboardingData.billingCycle === 'yearly'}
                      onChange={(e) =>
                        setOnboardingData((prev) => ({ ...prev, billingCycle: 'yearly' as const }))
                      }
                      className='focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300'
                    />
                    <span className='ml-2 text-sm text-gray-700'>
                      Yearly billing <span className='text-green-600'>(Save 20%)</span>
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        );

      case 'review':
        const selectedPlan = BILLING_PLANS.find((p) => p.id === onboardingData.billingPlan);
        const monthlyPrice = selectedPlan?.price || 0;
        const yearlyPrice =
          onboardingData.billingCycle === 'yearly' ? monthlyPrice * 12 * 0.8 : monthlyPrice;

        return (
          <div className='space-y-6'>
            <div>
              <h3 className='text-lg font-medium text-gray-900 mb-4'>Review & Deploy</h3>

              <div className='bg-gray-50 rounded-lg p-6 space-y-4'>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                  <div>
                    <h4 className='font-medium text-gray-900 mb-2'>Company Information</h4>
                    <div className='space-y-1 text-sm text-gray-600'>
                      <p>
                        <span className='font-medium'>Name:</span> {onboardingData.companyName}
                      </p>
                      <p>
                        <span className='font-medium'>Email:</span> {onboardingData.contactEmail}
                      </p>
                      <p>
                        <span className='font-medium'>Industry:</span> {onboardingData.industry}
                      </p>
                      <p>
                        <span className='font-medium'>Size:</span> {onboardingData.companySize}
                      </p>
                    </div>
                  </div>

                  <div>
                    <h4 className='font-medium text-gray-900 mb-2'>Technical Configuration</h4>
                    <div className='space-y-1 text-sm text-gray-600'>
                      <p>
                        <span className='font-medium'>URL:</span> https://{onboardingData.subdomain}
                        .dotmac.app
                      </p>
                      <p>
                        <span className='font-medium'>Timezone:</span> {onboardingData.timezone}
                      </p>
                      <p>
                        <span className='font-medium'>Currency:</span> {onboardingData.currency}
                      </p>
                      <p>
                        <span className='font-medium'>Language:</span> {onboardingData.language}
                      </p>
                    </div>
                  </div>

                  <div>
                    <h4 className='font-medium text-gray-900 mb-2'>Applications</h4>
                    <div className='text-sm text-gray-600'>
                      {onboardingData.selectedApps.map((appId) => {
                        const app = AVAILABLE_APPS.find((a) => a.id === appId);
                        return app ? <p key={appId}>• {app.name}</p> : null;
                      })}
                    </div>
                  </div>

                  <div>
                    <h4 className='font-medium text-gray-900 mb-2'>Infrastructure</h4>
                    <div className='space-y-1 text-sm text-gray-600'>
                      <p>
                        <span className='font-medium'>Region:</span>{' '}
                        {onboardingData.deploymentRegion}
                      </p>
                      <p>
                        <span className='font-medium'>Users:</span>{' '}
                        {onboardingData.userLimit === 0 ? 'Unlimited' : onboardingData.userLimit}
                      </p>
                      <p>
                        <span className='font-medium'>Storage:</span> {onboardingData.storageQuota}{' '}
                        GB
                      </p>
                      <p>
                        <span className='font-medium'>Bandwidth:</span>{' '}
                        {onboardingData.bandwidthLimit === 0
                          ? 'Unlimited'
                          : `${onboardingData.bandwidthLimit} GB/month`}
                      </p>
                    </div>
                  </div>
                </div>

                <div className='border-t pt-4'>
                  <div className='flex justify-between items-center'>
                    <div>
                      <h4 className='font-medium text-gray-900'>Billing Summary</h4>
                      <p className='text-sm text-gray-600'>
                        {selectedPlan?.name} Plan - {onboardingData.billingCycle} billing
                      </p>
                    </div>
                    <div className='text-right'>
                      <p className='text-2xl font-bold text-gray-900'>
                        $
                        {onboardingData.billingCycle === 'yearly'
                          ? yearlyPrice.toFixed(0)
                          : monthlyPrice}
                        <span className='text-sm font-normal'>
                          /{onboardingData.billingCycle === 'yearly' ? 'year' : 'month'}
                        </span>
                      </p>
                      {onboardingData.billingCycle === 'yearly' && (
                        <p className='text-sm text-green-600'>
                          Save ${(monthlyPrice * 12 - yearlyPrice).toFixed(0)}/year
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                <div className='bg-blue-50 border border-blue-200 rounded-md p-4'>
                  <div className='flex items-start'>
                    <ExclamationTriangleIcon className='h-5 w-5 text-blue-600 mt-0.5' />
                    <div className='ml-2'>
                      <h5 className='text-sm font-medium text-blue-800'>Deployment Information</h5>
                      <p className='text-sm text-blue-700 mt-1'>
                        Your tenant environment will be provisioned automatically. This process
                        typically takes 5-10 minutes. You'll receive an email confirmation once
                        deployment is complete.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className='fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50'>
      <div className='relative top-10 mx-auto p-5 border w-11/12 max-w-6xl shadow-lg rounded-md bg-white mb-10'>
        {/* Header */}
        <div className='flex items-center justify-between mb-8'>
          <div>
            <h2 className='text-2xl font-bold text-gray-900'>New Tenant Setup</h2>
            <p className='text-gray-600'>
              Step {currentStep + 1} of {STEPS.length}
            </p>
          </div>
          <button onClick={onCancel} className='text-gray-400 hover:text-gray-600'>
            <XMarkIcon className='h-6 w-6' />
          </button>
        </div>

        {/* Progress Steps */}
        <div className='mb-8'>
          <div className='flex items-center justify-between'>
            {STEPS.map((step, index) => {
              const Icon = step.icon;
              const isActive = index === currentStep;
              const isCompleted =
                index < currentStep || (index === currentStep && isStepComplete(index));

              return (
                <div key={step.id} className='flex items-center'>
                  <div
                    className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                      isCompleted
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : isActive
                          ? 'border-blue-600 text-blue-600'
                          : 'border-gray-300 text-gray-400'
                    }`}
                  >
                    {isCompleted && index < currentStep ? (
                      <CheckIcon className='h-6 w-6' />
                    ) : (
                      <Icon className='h-6 w-6' />
                    )}
                  </div>
                  <div className='ml-3'>
                    <p
                      className={`text-sm font-medium ${
                        isActive ? 'text-blue-600' : isCompleted ? 'text-gray-900' : 'text-gray-500'
                      }`}
                    >
                      {step.title}
                    </p>
                  </div>
                  {index < STEPS.length - 1 && (
                    <div
                      className={`w-full h-px mx-4 ${
                        index < currentStep ? 'bg-blue-600' : 'bg-gray-300'
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Step Content */}
        <div className='min-h-96 mb-8'>{renderStepContent()}</div>

        {/* Navigation */}
        <div className='flex items-center justify-between'>
          <button
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className='flex items-center space-x-2 px-4 py-2 text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed'
          >
            <ArrowLeftIcon className='h-4 w-4' />
            <span>Previous</span>
          </button>

          <div className='flex space-x-3'>
            <button
              onClick={onCancel}
              className='px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50'
            >
              Cancel
            </button>

            {currentStep === STEPS.length - 1 ? (
              <button
                onClick={handleSubmit}
                disabled={!canProceed || createTenantMutation.isPending}
                className='flex items-center space-x-2 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50'
              >
                {createTenantMutation.isPending ? (
                  <>
                    <LoadingSpinner size='small' />
                    <span>Creating Tenant...</span>
                  </>
                ) : (
                  <>
                    <CloudIcon className='h-4 w-4' />
                    <span>Deploy Tenant</span>
                  </>
                )}
              </button>
            ) : (
              <button
                onClick={handleNext}
                disabled={!canProceed}
                className='flex items-center space-x-2 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50'
              >
                <span>Next</span>
                <ArrowRightIcon className='h-4 w-4' />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
