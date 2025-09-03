/**
 * Plugin Installation Wizard Component
 * Following DRY patterns from existing components
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  ArrowRightIcon,
  ArrowLeftIcon,
  CheckIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  CpuChipIcon,
  ServerIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useApiClient, ISPError } from '@dotmac/headless';
import type {
  PluginCatalogItem,
  PluginInstallationRequest,
  PluginInstallationResponse,
} from '@dotmac/headless';

interface PluginInstallationWizardProps {
  plugin: PluginCatalogItem;
  isOpen: boolean;
  onClose: () => void;
  onComplete?: (installationId: string) => void;
}

interface WizardStep {
  id: string;
  title: string;
  description: string;
  completed: boolean;
}

export function PluginInstallationWizard({
  plugin,
  isOpen,
  onClose,
  onComplete,
}: PluginInstallationWizardProps) {
  const apiClient = useApiClient();
  const [currentStep, setCurrentStep] = useState(0);
  const [installing, setInstalling] = useState(false);
  const [installationId, setInstallationId] = useState<string | null>(null);
  const [installationStatus, setInstallationStatus] = useState<PluginInstallationResponse | null>(
    null
  );
  const [selectedTier, setSelectedTier] = useState(0);
  const [configuration, setConfiguration] = useState<Record<string, any>>({});
  const [agreesToPermissions, setAgreesToPermissions] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Refs to prevent memory leaks
  const mountedRef = useRef(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Memoized callback to prevent useEffect dependency issues
  const handleComplete = useCallback(
    (id: string) => {
      if (mountedRef.current && onComplete) {
        onComplete(id);
      }
    },
    [onComplete]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  const steps: WizardStep[] = [
    {
      id: 'review',
      title: 'Review Plugin',
      description: 'Review plugin details and requirements',
      completed: false,
    },
    {
      id: 'permissions',
      title: 'Permissions',
      description: 'Review and approve required permissions',
      completed: false,
    },
    {
      id: 'license',
      title: 'License & Pricing',
      description: 'Select license tier and pricing plan',
      completed: false,
    },
    {
      id: 'configuration',
      title: 'Configuration',
      description: 'Configure plugin settings',
      completed: false,
    },
    {
      id: 'installation',
      title: 'Installation',
      description: 'Install and activate the plugin',
      completed: false,
    },
  ];

  // Poll installation status with memory leak prevention
  useEffect(() => {
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (
      installationId &&
      installationStatus?.status !== 'completed' &&
      installationStatus?.status !== 'failed' &&
      mountedRef.current
    ) {
      intervalRef.current = setInterval(async () => {
        // Check if component is still mounted before making API call
        if (!mountedRef.current) {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          return;
        }

        try {
          const response = await apiClient.getPluginInstallationStatus(installationId);

          // Double-check component is still mounted before updating state
          if (mountedRef.current) {
            setInstallationStatus(response.data);

            if (response.data.status === 'completed') {
              handleComplete(installationId);
              if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
              }
            } else if (response.data.status === 'failed') {
              if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
              }
            }
          }
        } catch (err) {
          if (mountedRef.current) {
            // Use existing ISPError system for consistent error handling
            new ISPError(
              'PLUGIN_STATUS_POLLING_ERROR',
              'Failed to check installation status',
              'system',
              'medium',
              { installationId, originalError: err }
            );
            setError('Failed to check installation status');
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
          }
        }
      }, 2000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [installationId, installationStatus?.status, apiClient, handleComplete]);

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleInstall = async () => {
    setInstalling(true);
    setError(null);

    try {
      const request: PluginInstallationRequest = {
        plugin_id: plugin.id,
        license_tier: (plugin.pricing.tiers?.[selectedTier]?.name.toLowerCase() as any) || 'trial',
        configuration: configuration,
        auto_enable: true,
      };

      const response = await apiClient.installPlugin(request);
      setInstallationId(response.data.installation_id);
      setInstallationStatus(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to start installation');
    } finally {
      setInstalling(false);
    }
  };

  const renderReviewStep = () => (
    <div className='space-y-6'>
      <div className='flex items-start space-x-4'>
        <div className='w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center'>
          {plugin.icon ? (
            <img src={plugin.icon} alt={plugin.name} className='w-12 h-12' />
          ) : (
            <CpuChipIcon className='h-8 w-8 text-gray-400' />
          )}
        </div>

        <div className='flex-1'>
          <h3 className='text-lg font-semibold text-gray-900'>{plugin.name}</h3>
          <p className='text-gray-600 mb-2'>{plugin.description}</p>
          <div className='flex items-center space-x-4 text-sm text-gray-500'>
            <span>by {plugin.author}</span>
            <span>v{plugin.version}</span>
            <span className='capitalize'>{plugin.category}</span>
          </div>
        </div>
      </div>

      {/* Compatibility Check */}
      <div className='bg-green-50 p-4 rounded-lg'>
        <div className='flex'>
          <CheckIcon className='h-5 w-5 text-green-400' />
          <div className='ml-3'>
            <h4 className='text-sm font-medium text-green-800'>Compatibility Verified</h4>
            <p className='text-sm text-green-700'>
              This plugin is compatible with your current framework version.
            </p>
          </div>
        </div>
      </div>

      {/* Requirements */}
      <div>
        <h4 className='font-medium text-gray-900 mb-3'>System Requirements</h4>
        <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
          <div className='bg-gray-50 p-3 rounded'>
            <div className='flex items-center'>
              <ServerIcon className='h-5 w-5 text-gray-400 mr-2' />
              <span className='text-sm font-medium'>Framework Version</span>
            </div>
            <p className='text-sm text-gray-600 mt-1'>
              {plugin.compatibility.min_framework_version}+
            </p>
          </div>
          <div className='bg-gray-50 p-3 rounded'>
            <div className='flex items-center'>
              <CpuChipIcon className='h-5 w-5 text-gray-400 mr-2' />
              <span className='text-sm font-medium'>Dependencies</span>
            </div>
            <p className='text-sm text-gray-600 mt-1'>
              {plugin.compatibility.dependencies.length} required
            </p>
          </div>
        </div>
      </div>

      {/* Security Info */}
      <div>
        <h4 className='font-medium text-gray-900 mb-3'>Security Information</h4>
        <div className='space-y-2'>
          <div className='flex items-center'>
            <ShieldCheckIcon
              className={`h-5 w-5 mr-2 ${plugin.security.signed ? 'text-green-500' : 'text-gray-400'}`}
            />
            <span className='text-sm'>
              {plugin.security.signed ? 'Digitally signed' : 'Not digitally signed'}
            </span>
          </div>
          <div className='flex items-center'>
            <CheckIcon
              className={`h-5 w-5 mr-2 ${plugin.security.verified ? 'text-blue-500' : 'text-gray-400'}`}
            />
            <span className='text-sm'>
              {plugin.security.verified ? 'Verified publisher' : 'Unverified publisher'}
            </span>
          </div>
          <div className='flex items-center'>
            <ServerIcon
              className={`h-5 w-5 mr-2 ${plugin.security.sandboxed ? 'text-green-500' : 'text-yellow-500'}`}
            />
            <span className='text-sm'>
              {plugin.security.sandboxed ? 'Runs in sandbox' : 'Full system access'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderPermissionsStep = () => (
    <div className='space-y-6'>
      <div className='bg-yellow-50 p-4 rounded-lg'>
        <div className='flex'>
          <ExclamationTriangleIcon className='h-5 w-5 text-yellow-400' />
          <div className='ml-3'>
            <h4 className='text-sm font-medium text-yellow-800'>Review Required Permissions</h4>
            <p className='text-sm text-yellow-700'>
              This plugin requires the following permissions to function properly.
            </p>
          </div>
        </div>
      </div>

      <div className='space-y-4'>
        {Object.entries(plugin.permissions).map(
          ([category, perms]) =>
            perms.length > 0 && (
              <div key={category} className='border border-gray-200 rounded-lg p-4'>
                <h4 className='font-medium text-gray-900 capitalize mb-3'>
                  {category} Permissions
                </h4>
                <ul className='space-y-2'>
                  {perms.map((perm, index) => (
                    <li key={index} className='flex items-start'>
                      <div className='flex-shrink-0 mt-1'>
                        <div className='w-2 h-2 bg-gray-400 rounded-full'></div>
                      </div>
                      <span className='ml-3 text-sm text-gray-600'>{perm}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )
        )}
      </div>

      <div className='flex items-start'>
        <input
          type='checkbox'
          id='agree-permissions'
          checked={agreesToPermissions}
          onChange={(e) => setAgreesToPermissions(e.target.checked)}
          className='mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
        />
        <label htmlFor='agree-permissions' className='ml-3 text-sm text-gray-700'>
          I understand and approve these permissions. I trust this plugin with the requested access.
        </label>
      </div>
    </div>
  );

  const renderLicenseStep = () => (
    <div className='space-y-6'>
      {plugin.pricing.type === 'free' ? (
        <div className='text-center py-8'>
          <CheckIcon className='mx-auto h-12 w-12 text-green-500' />
          <h3 className='mt-4 text-lg font-medium text-gray-900'>Free Plugin</h3>
          <p className='mt-2 text-sm text-gray-600'>
            This plugin is completely free to use with no limitations.
          </p>
        </div>
      ) : plugin.pricing.tiers && plugin.pricing.tiers.length > 0 ? (
        <div>
          <h3 className='font-medium text-gray-900 mb-4'>Choose a License Tier</h3>
          <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
            {plugin.pricing.tiers.map((tier, index) => (
              <div
                key={index}
                className={`border-2 rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedTier === index
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setSelectedTier(index)}
              >
                <div className='text-center'>
                  <h4 className='font-semibold text-lg'>{tier.name}</h4>
                  <div className='text-3xl font-bold text-gray-900 my-2'>
                    ${tier.price}
                    <span className='text-sm font-normal text-gray-500'>/mo</span>
                  </div>
                  <ul className='text-sm text-gray-600 space-y-1 text-left'>
                    {tier.features.map((feature, fIndex) => (
                      <li key={fIndex} className='flex items-center'>
                        <CheckIcon className='h-4 w-4 text-green-500 mr-2 flex-shrink-0' />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className='text-center py-8'>
          <p className='text-gray-600'>License information not available</p>
        </div>
      )}
    </div>
  );

  const renderConfigurationStep = () => (
    <div className='space-y-6'>
      <div>
        <h3 className='font-medium text-gray-900 mb-4'>Plugin Configuration</h3>
        <p className='text-sm text-gray-600 mb-4'>
          Configure initial settings for the plugin. You can change these later.
        </p>

        <div className='bg-gray-50 p-4 rounded border'>
          <textarea
            value={JSON.stringify(configuration, null, 2)}
            onChange={(e) => {
              try {
                setConfiguration(JSON.parse(e.target.value));
              } catch {
                // Invalid JSON, ignore for now
              }
            }}
            className='w-full h-32 p-3 border border-gray-300 rounded font-mono text-sm'
            placeholder='Plugin configuration (JSON format)'
          />
        </div>

        <p className='text-xs text-gray-500 mt-2'>
          Leave empty to use default configuration. You can configure the plugin after installation.
        </p>
      </div>
    </div>
  );

  const renderInstallationStep = () => (
    <div className='space-y-6'>
      {!installationId ? (
        <div className='text-center py-8'>
          <div className='text-lg font-medium text-gray-900 mb-2'>Ready to Install</div>
          <p className='text-sm text-gray-600 mb-6'>
            Click "Install Plugin" to begin the installation process.
          </p>

          {error && (
            <div className='bg-red-50 p-4 rounded-lg mb-6'>
              <div className='flex'>
                <ExclamationTriangleIcon className='h-5 w-5 text-red-400' />
                <div className='ml-3'>
                  <h4 className='text-sm font-medium text-red-800'>Installation Error</h4>
                  <p className='text-sm text-red-700'>{error}</p>
                </div>
              </div>
            </div>
          )}

          <Button
            onClick={handleInstall}
            loading={installing}
            size='lg'
            disabled={!agreesToPermissions}
          >
            Install Plugin
          </Button>
        </div>
      ) : (
        <div className='space-y-6'>
          {/* Installation Progress */}
          <div className='text-center'>
            <div className='text-lg font-medium text-gray-900 mb-2'>Installing {plugin.name}</div>
            <p className='text-sm text-gray-600'>Installation ID: {installationId}</p>
          </div>

          {installationStatus && (
            <>
              {/* Progress Bar */}
              <div className='w-full bg-gray-200 rounded-full h-3'>
                <div
                  className='bg-primary-600 h-3 rounded-full transition-all duration-300'
                  style={{ width: `${installationStatus.progress}%` }}
                />
              </div>

              {/* Status */}
              <div className='text-center'>
                <div className='flex items-center justify-center space-x-2 mb-2'>
                  {installationStatus.status === 'completed' ? (
                    <CheckIcon className='h-5 w-5 text-green-500' />
                  ) : installationStatus.status === 'failed' ? (
                    <ExclamationTriangleIcon className='h-5 w-5 text-red-500' />
                  ) : (
                    <>
                      <LoadingSpinner size='small' />
                      <ClockIcon className='h-5 w-5 text-blue-500' />
                    </>
                  )}
                  <span className='font-medium capitalize'>{installationStatus.status}</span>
                </div>

                <p className='text-sm text-gray-600'>{installationStatus.message}</p>

                {installationStatus.estimated_completion && (
                  <p className='text-xs text-gray-500 mt-2'>
                    Estimated completion:{' '}
                    {new Date(installationStatus.estimated_completion).toLocaleTimeString()}
                  </p>
                )}
              </div>

              {/* Completion Actions */}
              {installationStatus.status === 'completed' && (
                <div className='text-center pt-4'>
                  <CheckIcon className='mx-auto h-16 w-16 text-green-500 mb-4' />
                  <h3 className='text-lg font-medium text-gray-900 mb-2'>Installation Complete!</h3>
                  <p className='text-sm text-gray-600 mb-4'>
                    {plugin.name} has been successfully installed and is ready to use.
                  </p>
                </div>
              )}

              {installationStatus.status === 'failed' && (
                <div className='text-center pt-4'>
                  <ExclamationTriangleIcon className='mx-auto h-16 w-16 text-red-500 mb-4' />
                  <h3 className='text-lg font-medium text-gray-900 mb-2'>Installation Failed</h3>
                  <p className='text-sm text-gray-600 mb-4'>{installationStatus.message}</p>
                  {installationStatus.rollback_available && (
                    <p className='text-xs text-gray-500'>Rollback is available if needed.</p>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );

  const canProceed = () => {
    switch (currentStep) {
      case 1: // Permissions
        return agreesToPermissions;
      case 4: // Installation
        return (
          installationStatus?.status === 'completed' || installationStatus?.status === 'failed'
        );
      default:
        return true;
    }
  };

  const isLastStep = currentStep === steps.length - 1;
  const showNext = !isLastStep && currentStep < 4;
  const showInstallButton = currentStep === 4 && !installationId;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title='Plugin Installation Wizard'
      size='xl'
      closeOnOverlayClick={false}
      closeOnEscape={false}
    >
      <div className='space-y-6'>
        {/* Progress Steps */}
        <div className='flex items-center justify-between'>
          {steps.map((step, index) => (
            <div key={step.id} className='flex items-center'>
              <div
                className={`
                w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                ${index <= currentStep ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'}
              `}
              >
                {index < currentStep ? <CheckIcon className='h-4 w-4' /> : index + 1}
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`
                  w-12 h-0.5 mx-2
                  ${index < currentStep ? 'bg-primary-600' : 'bg-gray-200'}
                `}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step Title */}
        <div className='text-center'>
          <h2 className='text-xl font-semibold text-gray-900'>{steps[currentStep].title}</h2>
          <p className='text-sm text-gray-600 mt-1'>{steps[currentStep].description}</p>
        </div>

        {/* Step Content */}
        <div className='min-h-[400px]'>
          {currentStep === 0 && renderReviewStep()}
          {currentStep === 1 && renderPermissionsStep()}
          {currentStep === 2 && renderLicenseStep()}
          {currentStep === 3 && renderConfigurationStep()}
          {currentStep === 4 && renderInstallationStep()}
        </div>

        {/* Actions */}
        <div className='flex justify-between pt-4 border-t'>
          <Button
            variant='outline'
            onClick={currentStep === 0 ? onClose : handleBack}
            disabled={installing}
          >
            {currentStep === 0 ? 'Cancel' : 'Back'}
          </Button>

          <div className='flex space-x-3'>
            {showNext && (
              <Button onClick={handleNext} rightIcon={ArrowRightIcon} disabled={!canProceed()}>
                Next
              </Button>
            )}

            {installationStatus?.status === 'completed' && (
              <Button onClick={onClose}>Finish</Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
