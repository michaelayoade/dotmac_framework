'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { WorkflowRunner, useWorkflow } from '@dotmac/workflows-system';
import type { WorkflowDefinition } from '@dotmac/workflows-system';
import { Button } from '@dotmac/primitives';
import { CheckCircle, User, CreditCard, Shield, Zap } from 'lucide-react';

interface CustomerOnboardingWorkflowProps {
  onComplete?: () => void;
  onSkip?: () => void;
  customerId?: string;
  className?: string;
}

const customerOnboardingDefinition: WorkflowDefinition = {
  id: 'customer_onboarding',
  name: 'Customer Onboarding',
  description: 'Welcome to your ISP service! Let\'s get you set up.',
  version: '1.0.0',
  category: 'onboarding',
  steps: [
    {
      id: 'welcome',
      name: 'Welcome',
      description: 'Welcome to your new ISP service',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            welcomeAcknowledged: {
              type: 'boolean',
              title: 'I understand and want to continue',
              description: 'Please acknowledge to continue with the setup process'
            }
          },
          required: ['welcomeAcknowledged']
        },
        layout: 'single-column'
      },
      canSkip: false,
      timeout: 300000 // 5 minutes
    },
    {
      id: 'profile_setup',
      name: 'Profile Setup',
      description: 'Complete your customer profile',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            firstName: {
              type: 'string',
              title: 'First Name',
              minLength: 1,
              maxLength: 50
            },
            lastName: {
              type: 'string',
              title: 'Last Name',
              minLength: 1,
              maxLength: 50
            },
            phoneNumber: {
              type: 'string',
              title: 'Phone Number',
              format: 'tel',
              pattern: '^[+]?[1-9]\\d{1,14}$'
            },
            preferredContactMethod: {
              type: 'string',
              title: 'Preferred Contact Method',
              enum: ['email', 'phone', 'sms'],
              enumNames: ['Email', 'Phone', 'SMS'],
              default: 'email'
            },
            marketingOptIn: {
              type: 'boolean',
              title: 'Receive service updates and offers',
              description: 'Stay informed about new features and special offers',
              default: false
            }
          },
          required: ['firstName', 'lastName', 'phoneNumber', 'preferredContactMethod']
        },
        layout: 'two-column',
        sections: [
          {
            title: 'Personal Information',
            description: 'Basic contact information',
            fields: ['firstName', 'lastName', 'phoneNumber']
          },
          {
            title: 'Communication Preferences',
            description: 'How would you like us to contact you?',
            fields: ['preferredContactMethod', 'marketingOptIn']
          }
        ]
      },
      canSkip: false
    },
    {
      id: 'service_preferences',
      name: 'Service Preferences',
      description: 'Configure your internet service preferences',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            primaryUseCase: {
              type: 'string',
              title: 'Primary Internet Use',
              enum: ['home_office', 'streaming', 'gaming', 'general', 'business'],
              enumNames: ['Home Office', 'Streaming', 'Gaming', 'General Use', 'Small Business']
            },
            speedRequirement: {
              type: 'string',
              title: 'Speed Requirement',
              enum: ['basic', 'standard', 'premium', 'ultra'],
              enumNames: ['Basic (25 Mbps)', 'Standard (100 Mbps)', 'Premium (500 Mbps)', 'Ultra (1 Gbps)']
            },
            wifiName: {
              type: 'string',
              title: 'WiFi Network Name',
              description: 'Custom name for your WiFi network',
              maxLength: 32,
              pattern: '^[a-zA-Z0-9_-]+$'
            },
            securityLevel: {
              type: 'string',
              title: 'Security Level',
              enum: ['standard', 'enhanced', 'maximum'],
              enumNames: ['Standard Protection', 'Enhanced Security', 'Maximum Security'],
              default: 'standard'
            },
            parentalControls: {
              type: 'boolean',
              title: 'Enable Parental Controls',
              description: 'Filter content and manage access times',
              default: false
            }
          },
          required: ['primaryUseCase', 'speedRequirement', 'wifiName', 'securityLevel']
        },
        layout: 'single-column'
      },
      canSkip: false
    },
    {
      id: 'payment_setup',
      name: 'Payment Setup',
      description: 'Set up your billing information',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            paymentMethod: {
              type: 'string',
              title: 'Payment Method',
              enum: ['credit_card', 'bank_transfer', 'paypal'],
              enumNames: ['Credit Card', 'Bank Transfer', 'PayPal']
            },
            billingCycle: {
              type: 'string',
              title: 'Billing Cycle',
              enum: ['monthly', 'quarterly', 'annually'],
              enumNames: ['Monthly', 'Quarterly (5% discount)', 'Annually (10% discount)'],
              default: 'monthly'
            },
            autopay: {
              type: 'boolean',
              title: 'Enable Automatic Payments',
              description: 'Automatically pay your bill each month',
              default: true
            },
            paperlessStatements: {
              type: 'boolean',
              title: 'Paperless Statements',
              description: 'Receive statements via email instead of mail',
              default: true
            }
          },
          required: ['paymentMethod', 'billingCycle']
        },
        layout: 'single-column'
      },
      canSkip: false
    },
    {
      id: 'equipment_delivery',
      name: 'Equipment Delivery',
      description: 'Schedule your equipment delivery and installation',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            installationType: {
              type: 'string',
              title: 'Installation Type',
              enum: ['self_install', 'professional', 'curbside'],
              enumNames: ['Self Installation (Free)', 'Professional Installation ($99)', 'Curbside Delivery ($25)']
            },
            deliveryDate: {
              type: 'string',
              title: 'Preferred Delivery Date',
              format: 'date',
              description: 'When would you like to receive your equipment?'
            },
            deliveryTimeSlot: {
              type: 'string',
              title: 'Time Slot',
              enum: ['morning', 'afternoon', 'evening', 'all_day'],
              enumNames: ['Morning (8 AM - 12 PM)', 'Afternoon (12 PM - 5 PM)', 'Evening (5 PM - 8 PM)', 'All Day']
            },
            specialInstructions: {
              type: 'string',
              title: 'Special Delivery Instructions',
              description: 'Any special instructions for delivery (optional)',
              format: 'textarea',
              maxLength: 500
            }
          },
          required: ['installationType', 'deliveryDate', 'deliveryTimeSlot']
        },
        layout: 'single-column'
      },
      canSkip: false
    },
    {
      id: 'confirmation',
      name: 'Confirmation',
      description: 'Review and confirm your setup',
      type: 'api_call',
      input: {
        url: '/api/customer/onboarding/complete',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        timeout: 10000
      },
      canSkip: false
    }
  ],
  metadata: {
    estimatedDuration: 600, // 10 minutes
    category: 'customer_onboarding',
    priority: 'high',
    tags: ['onboarding', 'customer', 'setup']
  }
};

export function CustomerOnboardingWorkflow({
  onComplete,
  onSkip,
  customerId,
  className
}: CustomerOnboardingWorkflowProps) {
  const [isStarted, setIsStarted] = useState(false);

  const {
    start: startWorkflow,
    pause,
    cancel,
    instance,
    isRunning,
    currentStep,
    progress
  } = useWorkflow({
    definition: customerOnboardingDefinition,
    onComplete: (result) => {
      console.log('Onboarding completed:', result);
      onComplete?.();
    },
    onError: (error) => {
      console.error('Onboarding error:', error);
    },
    onStepComplete: (stepId, output) => {
      console.log(`Step ${stepId} completed:`, output);
    },
    context: {
      customerId,
      startedAt: new Date().toISOString()
    }
  });

  const handleStart = () => {
    setIsStarted(true);
    startWorkflow();
  };

  const handleSkip = () => {
    cancel();
    onSkip?.();
  };

  // Welcome screen before starting workflow
  if (!isStarted) {
    return (
      <div className={`onboarding-welcome ${className || ''}`}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="welcome-container max-w-2xl mx-auto text-center p-8"
        >
          <div className="welcome-icon mb-6">
            <Zap className="w-16 h-16 text-blue-600 mx-auto" />
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Welcome to Your New Internet Service!
          </h1>

          <p className="text-lg text-gray-600 mb-8">
            We'll help you get set up in just a few minutes. This process includes:
          </p>

          <div className="setup-steps grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
              <User className="w-6 h-6 text-blue-600 flex-shrink-0" />
              <span className="text-sm">Complete your profile</span>
            </div>
            <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
              <Shield className="w-6 h-6 text-blue-600 flex-shrink-0" />
              <span className="text-sm">Configure service preferences</span>
            </div>
            <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
              <CreditCard className="w-6 h-6 text-blue-600 flex-shrink-0" />
              <span className="text-sm">Set up billing</span>
            </div>
            <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
              <CheckCircle className="w-6 h-6 text-blue-600 flex-shrink-0" />
              <span className="text-sm">Schedule equipment delivery</span>
            </div>
          </div>

          <div className="estimated-time mb-8">
            <p className="text-sm text-gray-500">
              Estimated time: 5-10 minutes
            </p>
          </div>

          <div className="action-buttons flex gap-4 justify-center">
            <Button
              onClick={handleStart}
              size="lg"
              className="min-w-32"
            >
              Get Started
            </Button>

            {onSkip && (
              <Button
                onClick={handleSkip}
                variant="outline"
                size="lg"
                className="min-w-32"
              >
                Skip Setup
              </Button>
            )}
          </div>

          <p className="text-xs text-gray-400 mt-4">
            You can always complete this setup later from your dashboard
          </p>
        </motion.div>
      </div>
    );
  }

  // Show workflow runner when started
  return (
    <div className={`customer-onboarding-workflow ${className || ''}`}>
      <WorkflowRunner
        workflowId={instance?.id}
        showProgress={true}
        showStepNavigation={true}
        className="max-w-4xl mx-auto"
        onCancel={handleSkip}
      />
    </div>
  );
}

export default CustomerOnboardingWorkflow;
