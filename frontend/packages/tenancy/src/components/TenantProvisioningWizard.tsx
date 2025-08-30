import React, { useState, useCallback, useEffect } from 'react';
import { Button } from '@dotmac/primitives';
import type { TenantProvisioningRequest, TenantProvisioningStatus, TenantBranding, ResourceLimits } from '../types';
import { useTenantManagement } from '../hooks/useTenantManagement';

export interface TenantProvisioningWizardProps {
  onComplete?: (tenantId: string) => void;
  onCancel?: () => void;
  className?: string;
}

interface WizardStep {
  id: string;
  title: string;
  description: string;
  isComplete: boolean;
  isOptional?: boolean;
}

interface FormData extends Omit<TenantProvisioningRequest, 'adminUser'> {
  adminUser: {
    email: string;
    firstName: string;
    lastName: string;
    phone: string;
  };
}

const INITIAL_FORM_DATA: FormData = {
  name: '',
  slug: '',
  domain: '',
  tier: 'basic',
  adminUser: {
    email: '',
    firstName: '',
    lastName: '',
    phone: '',
  },
  branding: {
    companyName: '',
    primaryColor: '#2563eb',
    secondaryColor: '#64748b',
  },
  features: [],
  customLimits: {
    users: 10,
    storage: 1024 * 1024 * 1024, // 1GB
    bandwidth: 10 * 1024 * 1024 * 1024, // 10GB
    apiCalls: 10000,
    customDomains: 1,
    projects: 5,
  },
  metadata: {},
};

const TIER_LIMITS: Record<string, ResourceLimits> = {
  basic: {
    users: 10,
    storage: 1024 * 1024 * 1024, // 1GB
    bandwidth: 10 * 1024 * 1024 * 1024, // 10GB
    apiCalls: 10000,
    customDomains: 1,
    projects: 5,
  },
  professional: {
    users: 50,
    storage: 10 * 1024 * 1024 * 1024, // 10GB
    bandwidth: 100 * 1024 * 1024 * 1024, // 100GB
    apiCalls: 100000,
    customDomains: 5,
    projects: 25,
  },
  enterprise: {
    users: -1, // unlimited
    storage: 100 * 1024 * 1024 * 1024, // 100GB
    bandwidth: 1000 * 1024 * 1024 * 1024, // 1TB
    apiCalls: 1000000,
    customDomains: -1, // unlimited
    projects: -1, // unlimited
  },
};

export function TenantProvisioningWizard({ onComplete, onCancel, className }: TenantProvisioningWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<FormData>(INITIAL_FORM_DATA);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [requestId, setRequestId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { actions, provisioning, error } = useTenantManagement();

  const steps: WizardStep[] = [
    {
      id: 'basic-info',
      title: 'Basic Information',
      description: 'Configure tenant name, slug, and tier',
      isComplete: !!(formData.name && formData.slug && formData.tier),
    },
    {
      id: 'admin-user',
      title: 'Admin User',
      description: 'Set up the initial administrator account',
      isComplete: !!(formData.adminUser.email && formData.adminUser.firstName && formData.adminUser.lastName),
    },
    {
      id: 'branding',
      title: 'Branding',
      description: 'Customize the tenant appearance',
      isComplete: !!(formData.branding?.companyName),
      isOptional: true,
    },
    {
      id: 'resources',
      title: 'Resources',
      description: 'Configure resource limits and quotas',
      isComplete: true,
      isOptional: true,
    },
    {
      id: 'review',
      title: 'Review & Confirm',
      description: 'Review all settings before provisioning',
      isComplete: true,
    },
  ];

  // Auto-update slug when name changes
  useEffect(() => {
    if (formData.name && !formData.slug) {
      const slug = formData.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
      setFormData(prev => ({ ...prev, slug }));
    }
  }, [formData.name]);

  // Update resource limits when tier changes
  useEffect(() => {
    if (formData.tier) {
      setFormData(prev => ({
        ...prev,
        customLimits: { ...TIER_LIMITS[formData.tier] }
      }));
    }
  }, [formData.tier]);

  // Check provisioning status
  useEffect(() => {
    if (requestId && provisioning?.status !== 'completed' && provisioning?.status !== 'failed') {
      const interval = setInterval(() => {
        actions.checkProvisioningStatus(requestId);
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [requestId, provisioning, actions]);

  // Handle completion
  useEffect(() => {
    if (provisioning?.status === 'completed' && provisioning.tenantId) {
      onComplete?.(provisioning.tenantId);
    }
  }, [provisioning, onComplete]);

  const updateFormData = useCallback((updates: Partial<FormData>) => {
    setFormData(prev => ({ ...prev, ...updates }));
    // Clear validation errors for updated fields
    const updatedFields = Object.keys(updates);
    setValidationErrors(prev => {
      const newErrors = { ...prev };
      updatedFields.forEach(field => delete newErrors[field]);
      return newErrors;
    });
  }, []);

  const validateStep = useCallback((stepIndex: number): boolean => {
    const errors: Record<string, string> = {};

    switch (stepIndex) {
      case 0: // Basic Info
        if (!formData.name) errors.name = 'Tenant name is required';
        if (!formData.slug) errors.slug = 'Tenant slug is required';
        if (!/^[a-z0-9-]+$/.test(formData.slug)) errors.slug = 'Slug must contain only lowercase letters, numbers, and hyphens';
        break;

      case 1: // Admin User
        if (!formData.adminUser.email) errors.adminEmail = 'Admin email is required';
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.adminUser.email)) errors.adminEmail = 'Valid email is required';
        if (!formData.adminUser.firstName) errors.adminFirstName = 'First name is required';
        if (!formData.adminUser.lastName) errors.adminLastName = 'Last name is required';
        break;
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formData]);

  const handleNext = useCallback(() => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, steps.length - 1));
    }
  }, [currentStep, validateStep, steps.length]);

  const handlePrevious = useCallback(() => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!validateStep(currentStep)) return;

    setIsSubmitting(true);

    try {
      const request: TenantProvisioningRequest = {
        name: formData.name,
        slug: formData.slug,
        domain: formData.domain || undefined,
        tier: formData.tier,
        adminUser: {
          email: formData.adminUser.email,
          firstName: formData.adminUser.firstName,
          lastName: formData.adminUser.lastName,
          phone: formData.adminUser.phone || undefined,
        },
        branding: formData.branding,
        features: formData.features,
        customLimits: formData.customLimits,
        metadata: formData.metadata,
      };

      const newRequestId = await actions.provisionTenant(request);
      setRequestId(newRequestId);

      // Move to next step to show progress
      setCurrentStep(steps.length);
    } catch (err) {
      console.error('Failed to provision tenant:', err);
    } finally {
      setIsSubmitting(false);
    }
  }, [currentStep, validateStep, formData, actions, steps.length]);

  const renderStepContent = () => {
    if (requestId && currentStep >= steps.length) {
      return (
        <div className="space-y-6">
          <div className="text-center">
            <h3 className="text-lg font-medium mb-4">Provisioning Tenant</h3>
            {provisioning && (
              <div className="space-y-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${provisioning.progress}%` }}
                  />
                </div>
                <p className="text-sm text-gray-600">{provisioning.currentStep}</p>
                {provisioning.status === 'failed' && (
                  <p className="text-red-600 text-sm">{provisioning.error}</p>
                )}
                {provisioning.status === 'completed' && (
                  <p className="text-green-600 text-sm">Tenant provisioned successfully!</p>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }

    switch (currentStep) {
      case 0: // Basic Info
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Tenant Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => updateFormData({ name: e.target.value })}
                className="w-full p-2 border rounded"
                placeholder="My Company"
              />
              {validationErrors.name && (
                <p className="text-red-600 text-sm mt-1">{validationErrors.name}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Tenant Slug *</label>
              <input
                type="text"
                value={formData.slug}
                onChange={(e) => updateFormData({ slug: e.target.value })}
                className="w-full p-2 border rounded"
                placeholder="my-company"
              />
              {validationErrors.slug && (
                <p className="text-red-600 text-sm mt-1">{validationErrors.slug}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Custom Domain (optional)</label>
              <input
                type="text"
                value={formData.domain}
                onChange={(e) => updateFormData({ domain: e.target.value })}
                className="w-full p-2 border rounded"
                placeholder="my-company.example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Tier *</label>
              <select
                value={formData.tier}
                onChange={(e) => updateFormData({ tier: e.target.value as any })}
                className="w-full p-2 border rounded"
              >
                <option value="basic">Basic</option>
                <option value="professional">Professional</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </div>
          </div>
        );

      case 1: // Admin User
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email *</label>
              <input
                type="email"
                value={formData.adminUser.email}
                onChange={(e) => updateFormData({
                  adminUser: { ...formData.adminUser, email: e.target.value }
                })}
                className="w-full p-2 border rounded"
                placeholder="admin@company.com"
              />
              {validationErrors.adminEmail && (
                <p className="text-red-600 text-sm mt-1">{validationErrors.adminEmail}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">First Name *</label>
                <input
                  type="text"
                  value={formData.adminUser.firstName}
                  onChange={(e) => updateFormData({
                    adminUser: { ...formData.adminUser, firstName: e.target.value }
                  })}
                  className="w-full p-2 border rounded"
                  placeholder="John"
                />
                {validationErrors.adminFirstName && (
                  <p className="text-red-600 text-sm mt-1">{validationErrors.adminFirstName}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Last Name *</label>
                <input
                  type="text"
                  value={formData.adminUser.lastName}
                  onChange={(e) => updateFormData({
                    adminUser: { ...formData.adminUser, lastName: e.target.value }
                  })}
                  className="w-full p-2 border rounded"
                  placeholder="Doe"
                />
                {validationErrors.adminLastName && (
                  <p className="text-red-600 text-sm mt-1">{validationErrors.adminLastName}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Phone (optional)</label>
              <input
                type="tel"
                value={formData.adminUser.phone}
                onChange={(e) => updateFormData({
                  adminUser: { ...formData.adminUser, phone: e.target.value }
                })}
                className="w-full p-2 border rounded"
                placeholder="+1 (555) 123-4567"
              />
            </div>
          </div>
        );

      case 2: // Branding
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Company Name</label>
              <input
                type="text"
                value={formData.branding?.companyName || ''}
                onChange={(e) => updateFormData({
                  branding: { ...formData.branding!, companyName: e.target.value }
                })}
                className="w-full p-2 border rounded"
                placeholder="My Company Inc."
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Primary Color</label>
                <input
                  type="color"
                  value={formData.branding?.primaryColor || '#2563eb'}
                  onChange={(e) => updateFormData({
                    branding: { ...formData.branding!, primaryColor: e.target.value }
                  })}
                  className="w-full h-10 border rounded"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Secondary Color</label>
                <input
                  type="color"
                  value={formData.branding?.secondaryColor || '#64748b'}
                  onChange={(e) => updateFormData({
                    branding: { ...formData.branding!, secondaryColor: e.target.value }
                  })}
                  className="w-full h-10 border rounded"
                />
              </div>
            </div>
          </div>
        );

      case 3: // Resources
        return (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Resource limits for {formData.tier} tier. You can customize these values.
            </p>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Max Users</label>
                <input
                  type="number"
                  value={formData.customLimits?.users || 0}
                  onChange={(e) => updateFormData({
                    customLimits: { ...formData.customLimits!, users: parseInt(e.target.value) }
                  })}
                  className="w-full p-2 border rounded"
                  min="1"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Max Projects</label>
                <input
                  type="number"
                  value={formData.customLimits?.projects || 0}
                  onChange={(e) => updateFormData({
                    customLimits: { ...formData.customLimits!, projects: parseInt(e.target.value) }
                  })}
                  className="w-full p-2 border rounded"
                  min="1"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">API Calls per Month</label>
              <input
                type="number"
                value={formData.customLimits?.apiCalls || 0}
                onChange={(e) => updateFormData({
                  customLimits: { ...formData.customLimits!, apiCalls: parseInt(e.target.value) }
                })}
                className="w-full p-2 border rounded"
                min="1000"
              />
            </div>
          </div>
        );

      case 4: // Review
        return (
          <div className="space-y-6">
            <div>
              <h4 className="font-medium mb-2">Basic Information</h4>
              <div className="bg-gray-50 p-4 rounded space-y-2">
                <p><strong>Name:</strong> {formData.name}</p>
                <p><strong>Slug:</strong> {formData.slug}</p>
                <p><strong>Tier:</strong> {formData.tier}</p>
                {formData.domain && <p><strong>Domain:</strong> {formData.domain}</p>}
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-2">Administrator</h4>
              <div className="bg-gray-50 p-4 rounded space-y-2">
                <p><strong>Name:</strong> {formData.adminUser.firstName} {formData.adminUser.lastName}</p>
                <p><strong>Email:</strong> {formData.adminUser.email}</p>
                {formData.adminUser.phone && <p><strong>Phone:</strong> {formData.adminUser.phone}</p>}
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded p-4">
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  if (requestId && currentStep >= steps.length) {
    return (
      <div className={`max-w-2xl mx-auto ${className}`}>
        <div className="bg-white rounded-lg shadow-lg p-6">
          {renderStepContent()}

          <div className="mt-6 flex justify-between">
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={provisioning?.status === 'provisioning'}
            >
              {provisioning?.status === 'completed' ? 'Close' : 'Cancel'}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`max-w-2xl mx-auto ${className}`}>
      <div className="bg-white rounded-lg shadow-lg">
        {/* Progress indicator */}
        <div className="p-6 border-b">
          <div className="flex items-center justify-between mb-4">
            {steps.map((step, index) => (
              <div
                key={step.id}
                className={`flex items-center ${index < steps.length - 1 ? 'flex-1' : ''}`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    index === currentStep
                      ? 'bg-blue-600 text-white'
                      : index < currentStep || step.isComplete
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {index < currentStep || step.isComplete ? '✓' : index + 1}
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`flex-1 h-1 mx-4 ${
                      index < currentStep ? 'bg-green-600' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          <div>
            <h2 className="text-xl font-semibold">{steps[currentStep]?.title}</h2>
            <p className="text-gray-600 text-sm">{steps[currentStep]?.description}</p>
          </div>
        </div>

        {/* Step content */}
        <div className="p-6">
          {renderStepContent()}
        </div>

        {/* Navigation */}
        <div className="px-6 py-4 border-t flex justify-between">
          <Button
            variant="outline"
            onClick={currentStep === 0 ? onCancel : handlePrevious}
          >
            {currentStep === 0 ? 'Cancel' : 'Previous'}
          </Button>

          <Button
            onClick={currentStep === steps.length - 1 ? handleSubmit : handleNext}
            disabled={isSubmitting}
          >
            {isSubmitting
              ? 'Provisioning...'
              : currentStep === steps.length - 1
              ? 'Provision Tenant'
              : 'Next'
            }
          </Button>
        </div>
      </div>
    </div>
  );
}
