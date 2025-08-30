// Main exports for journey orchestration package
export * from './types';

// Core classes
export { JourneyOrchestrator } from './orchestrator/JourneyOrchestrator';
export { JourneyEventBus } from './events/EventBus';
export { ConversionAnalytics } from './analytics/ConversionAnalytics';
export { HandoffSystem } from './handoffs/HandoffSystem';

// React hooks
export { useJourneyOrchestration } from './hooks/useJourneyOrchestration';
export { useConversionAnalytics } from './hooks/useConversionAnalytics';
export { useHandoffSystem } from './hooks/useHandoffSystem';

// Journey templates for common ISP workflows
export const ISP_JOURNEY_TEMPLATES = {
  // Customer acquisition journey
  CUSTOMER_ACQUISITION: {
    id: 'customer_acquisition',
    name: 'Customer Acquisition Journey',
    description: 'Lead to customer conversion with service activation',
    category: 'acquisition',
    version: '1.0.0',
    steps: [
      {
        id: 'lead_qualification',
        name: 'Lead Qualification',
        description: 'Qualify lead and assess service needs',
        stage: 'lead',
        order: 1,
        type: 'manual',
        packageName: 'crm',
        estimatedDuration: 30,
        entryConditions: [
          { field: 'leadScore', operator: 'greater_than', value: 50 }
        ]
      },
      {
        id: 'customer_conversion',
        name: 'Convert to Customer',
        description: 'Convert qualified lead to customer account',
        stage: 'customer',
        order: 2,
        type: 'integration',
        packageName: 'crm',
        actionType: 'convert_lead',
        estimatedDuration: 15,
        integration: {
          package: 'crm',
          api: '/api/crm/leads/{leadId}/convert'
        }
      },
      {
        id: 'service_selection',
        name: 'Service Selection',
        description: 'Customer selects service plan and options',
        stage: 'customer',
        order: 3,
        type: 'manual',
        packageName: 'business-logic',
        estimatedDuration: 45
      },
      {
        id: 'service_activation',
        name: 'Service Activation',
        description: 'Activate customer service and billing',
        stage: 'active_service',
        order: 4,
        type: 'integration',
        packageName: 'business-logic',
        actionType: 'activate_service',
        estimatedDuration: 30,
        integration: {
          package: 'business-logic',
          api: '/api/services/activate'
        }
      },
      {
        id: 'installation_schedule',
        name: 'Schedule Installation',
        description: 'Schedule technician for service installation',
        stage: 'active_service',
        order: 5,
        type: 'integration',
        packageName: 'field-ops',
        actionType: 'schedule_installation',
        estimatedDuration: 20,
        integration: {
          package: 'field-ops',
          api: '/api/work-orders/schedule'
        }
      }
    ],
    defaultContext: {
      priority: 'medium',
      autoProgress: true
    },
    triggers: [
      {
        id: 'lead_qualified_trigger',
        name: 'Lead Qualified',
        type: 'event',
        event: 'crm:lead_qualified',
        templateId: 'customer_acquisition',
        isActive: true,
        priority: 1
      }
    ],
    settings: {
      autoProgress: true,
      allowSkipSteps: true,
      notificationsEnabled: true,
      slaTracking: true
    }
  },

  // Support resolution journey
  SUPPORT_RESOLUTION: {
    id: 'support_resolution',
    name: 'Support Resolution Journey',
    description: 'Customer support ticket resolution workflow',
    category: 'support',
    version: '1.0.0',
    steps: [
      {
        id: 'ticket_triage',
        name: 'Ticket Triage',
        description: 'Categorize and prioritize support ticket',
        stage: 'support',
        order: 1,
        type: 'automated',
        packageName: 'support-system',
        estimatedDuration: 5
      },
      {
        id: 'agent_assignment',
        name: 'Agent Assignment',
        description: 'Assign ticket to appropriate support agent',
        stage: 'support',
        order: 2,
        type: 'automated',
        packageName: 'support-system',
        estimatedDuration: 2
      },
      {
        id: 'issue_diagnosis',
        name: 'Issue Diagnosis',
        description: 'Diagnose customer issue',
        stage: 'support',
        order: 3,
        type: 'manual',
        packageName: 'support-system',
        estimatedDuration: 60
      },
      {
        id: 'resolution_action',
        name: 'Resolution Action',
        description: 'Take action to resolve customer issue',
        stage: 'support',
        order: 4,
        type: 'manual',
        packageName: 'support-system',
        estimatedDuration: 45
      },
      {
        id: 'customer_verification',
        name: 'Customer Verification',
        description: 'Verify resolution with customer',
        stage: 'support',
        order: 5,
        type: 'manual',
        packageName: 'support-system',
        estimatedDuration: 15
      }
    ],
    defaultContext: {
      priority: 'high',
      slaHours: 4
    },
    triggers: [
      {
        id: 'ticket_created_trigger',
        name: 'Support Ticket Created',
        type: 'event',
        event: 'support:ticket_created',
        templateId: 'support_resolution',
        isActive: true,
        priority: 1
      }
    ],
    settings: {
      autoProgress: false,
      allowSkipSteps: false,
      notificationsEnabled: true,
      slaTracking: true
    }
  },

  // Customer onboarding journey
  CUSTOMER_ONBOARDING: {
    id: 'customer_onboarding',
    name: 'Customer Onboarding Journey',
    description: 'New customer onboarding and setup',
    category: 'onboarding',
    version: '1.0.0',
    steps: [
      {
        id: 'welcome_communication',
        name: 'Welcome Communication',
        description: 'Send welcome email and setup instructions',
        stage: 'customer',
        order: 1,
        type: 'notification',
        packageName: 'communication-system',
        estimatedDuration: 5
      },
      {
        id: 'billing_setup',
        name: 'Billing Setup',
        description: 'Set up customer billing and payment methods',
        stage: 'customer',
        order: 2,
        type: 'integration',
        packageName: 'billing-system',
        actionType: 'setup_billing',
        estimatedDuration: 30,
        integration: {
          package: 'billing-system',
          api: '/api/billing/accounts'
        }
      },
      {
        id: 'equipment_provisioning',
        name: 'Equipment Provisioning',
        description: 'Provision and configure customer equipment',
        stage: 'active_service',
        order: 3,
        type: 'integration',
        packageName: 'business-logic',
        actionType: 'provision_equipment',
        estimatedDuration: 60
      },
      {
        id: 'service_testing',
        name: 'Service Testing',
        description: 'Test service connectivity and functionality',
        stage: 'active_service',
        order: 4,
        type: 'integration',
        packageName: 'field-ops',
        actionType: 'test_service',
        estimatedDuration: 30
      },
      {
        id: 'onboarding_complete',
        name: 'Onboarding Complete',
        description: 'Finalize onboarding and send confirmation',
        stage: 'active_service',
        order: 5,
        type: 'notification',
        packageName: 'communication-system',
        estimatedDuration: 10
      }
    ],
    defaultContext: {
      priority: 'medium',
      autoProgress: true
    },
    triggers: [
      {
        id: 'service_activated_trigger',
        name: 'Service Activated',
        type: 'event',
        event: 'service:activated',
        templateId: 'customer_onboarding',
        isActive: true,
        priority: 1
      }
    ],
    settings: {
      autoProgress: true,
      allowSkipSteps: true,
      notificationsEnabled: true,
      slaTracking: true
    }
  }
} as const;

// Utility functions for journey management
export const JourneyUtils = {
  /**
   * Create a journey template from configuration
   */
  createTemplate: (config: any) => ({
    ...config,
    id: config.id || `template_${Date.now()}`,
    version: config.version || '1.0.0',
    createdAt: new Date().toISOString(),
    isActive: true,
    estimatedDuration: config.steps?.reduce((sum: number, step: any) => sum + (step.estimatedDuration || 0), 0) || 0,
    usageCount: 0
  }),

  /**
   * Validate journey template structure
   */
  validateTemplate: (template: any): { isValid: boolean; errors: string[] } => {
    const errors: string[] = [];

    if (!template.id) errors.push('Template ID is required');
    if (!template.name) errors.push('Template name is required');
    if (!template.steps || !Array.isArray(template.steps)) errors.push('Template steps array is required');
    if (template.steps && template.steps.length === 0) errors.push('Template must have at least one step');

    // Validate steps
    if (template.steps) {
      template.steps.forEach((step: any, index: number) => {
        if (!step.id) errors.push(`Step ${index + 1}: ID is required`);
        if (!step.name) errors.push(`Step ${index + 1}: Name is required`);
        if (!step.stage) errors.push(`Step ${index + 1}: Stage is required`);
        if (typeof step.order !== 'number') errors.push(`Step ${index + 1}: Order must be a number`);
      });
    }

    return { isValid: errors.length === 0, errors };
  },

  /**
   * Get step dependencies
   */
  getStepDependencies: (template: any, stepId: string): string[] => {
    const step = template.steps?.find((s: any) => s.id === stepId);
    return step?.dependencies || [];
  },

  /**
   * Calculate journey completion percentage
   */
  calculateProgress: (completedSteps: string[], totalSteps: number): number => {
    if (totalSteps === 0) return 0;
    return Math.round((completedSteps.length / totalSteps) * 100);
  },

  /**
   * Estimate journey completion time
   */
  estimateCompletion: (template: any, currentStepId: string): number => {
    const currentStepIndex = template.steps?.findIndex((s: any) => s.id === currentStepId) || 0;
    const remainingSteps = template.steps?.slice(currentStepIndex + 1) || [];

    return remainingSteps.reduce((sum: number, step: any) => sum + (step.estimatedDuration || 0), 0);
  }
};
