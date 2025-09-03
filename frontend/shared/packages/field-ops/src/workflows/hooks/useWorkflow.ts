import { useState, useEffect, useCallback } from 'react';
import { useAuth, useApiClient } from '@dotmac/headless';
import type {
  WorkflowInstance,
  WorkflowStep,
  WorkflowTemplate,
  StepEvidence,
  WorkflowValidationResult,
} from '../types';

interface UseWorkflowOptions {
  workOrderId: string;
  templateId?: string;
  autoSave?: boolean;
  saveInterval?: number;
}

interface UseWorkflowReturn {
  // State
  workflow: WorkflowInstance | null;
  currentStep: WorkflowStep | null;
  loading: boolean;
  error: string | null;

  // Progress
  progress: number;
  completedSteps: number;
  totalSteps: number;
  estimatedTimeRemaining: number;

  // Actions
  startWorkflow: () => Promise<void>;
  completeWorkflow: () => Promise<void>;
  pauseWorkflow: () => Promise<void>;
  cancelWorkflow: () => Promise<void>;

  // Step management
  startStep: (stepId: string) => Promise<void>;
  completeStep: (
    stepId: string,
    data: Record<string, any>,
    evidence: StepEvidence[]
  ) => Promise<void>;
  skipStep: (stepId: string, reason?: string) => Promise<void>;
  pauseStep: (stepId: string) => Promise<void>;
  goToStep: (stepId: string) => Promise<void>;

  // Navigation
  canGoToStep: (stepId: string) => boolean;
  getNextStep: () => WorkflowStep | null;
  getPreviousStep: () => WorkflowStep | null;

  // Validation
  validateWorkflow: () => WorkflowValidationResult;
  validateStep: (stepId: string) => boolean;

  // Data management
  updateStepData: (stepId: string, data: Record<string, any>) => void;
  addStepEvidence: (stepId: string, evidence: StepEvidence) => void;
  removeStepEvidence: (stepId: string, evidenceId: string) => void;

  // Sync
  saveWorkflow: () => Promise<void>;
  syncWithServer: () => Promise<void>;

  // Customer interaction
  setCustomerPresent: (present: boolean) => void;
  addCustomerSignature: (signature: StepEvidence) => void;
  addCustomerFeedback: (rating: number, comments: string) => void;
}

export function useWorkflow(options: UseWorkflowOptions): UseWorkflowReturn {
  const { workOrderId, templateId, autoSave = true, saveInterval = 30000 } = options;
  const { user, tenantId } = useAuth();
  const apiClient = useApiClient();

  const [workflow, setWorkflow] = useState<WorkflowInstance | null>(null);
  const [currentStep, setCurrentStep] = useState<WorkflowStep | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load workflow
  const loadWorkflow = useCallback(async () => {
    if (!workOrderId || !user?.id) return;

    try {
      setLoading(true);
      setError(null);

      // Try to load existing workflow
      const response = await apiClient.get(`/field-ops/workflows/work-order/${workOrderId}`);

      if (response.data?.workflow) {
        const loadedWorkflow = response.data.workflow as WorkflowInstance;
        setWorkflow(loadedWorkflow);

        // Set current step
        if (loadedWorkflow.currentStepId) {
          const step = loadedWorkflow.steps.find((s) => s.id === loadedWorkflow.currentStepId);
          setCurrentStep(step || null);
        }
      } else if (templateId) {
        // Create new workflow from template
        const templateResponse = await apiClient.get(`/field-ops/workflow-templates/${templateId}`);

        if (templateResponse.data?.template) {
          const template = templateResponse.data.template as WorkflowTemplate;
          const newWorkflow = createWorkflowFromTemplate(template, workOrderId, user.id);

          // Save new workflow
          await apiClient.post('/field-ops/workflows', newWorkflow);
          setWorkflow(newWorkflow);
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load workflow';
      setError(errorMessage);
      console.error('Failed to load workflow:', err);
    } finally {
      setLoading(false);
    }
  }, [workOrderId, templateId, user?.id, apiClient]);

  // Create workflow from template
  const createWorkflowFromTemplate = (
    template: WorkflowTemplate,
    workOrderId: string,
    technicianId: string
  ): WorkflowInstance => {
    const now = new Date().toISOString();

    return {
      id: `workflow_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      templateId: template.id,
      workOrderId,
      technicianId,
      currentStepId: null,
      status: 'not_started',
      progress: 0,
      steps: template.steps.map((step) => ({
        ...step,
        status: 'pending',
        data: {},
        evidence: [],
      })),
      customerPresent: false,
      syncStatus: 'pending',
      lastModified: now,
    };
  };

  // Calculate progress
  const calculateProgress = useCallback((workflowInstance: WorkflowInstance) => {
    const completedSteps = workflowInstance.steps.filter((s) => s.status === 'completed').length;
    const totalSteps = workflowInstance.steps.length;
    return totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
  }, []);

  // Update workflow state
  const updateWorkflow = useCallback(
    (updates: Partial<WorkflowInstance>) => {
      if (!workflow) return;

      const updatedWorkflow = {
        ...workflow,
        ...updates,
        lastModified: new Date().toISOString(),
        syncStatus: 'pending' as const,
      };

      // Calculate progress
      updatedWorkflow.progress = calculateProgress(updatedWorkflow);

      setWorkflow(updatedWorkflow);

      // Auto-save if enabled
      if (autoSave) {
        saveWorkflow();
      }
    },
    [workflow, calculateProgress, autoSave]
  );

  // Workflow actions
  const startWorkflow = useCallback(async () => {
    if (!workflow) return;

    const now = new Date().toISOString();
    updateWorkflow({
      status: 'in_progress',
      startedAt: now,
      currentStepId: workflow.steps[0]?.id || null,
    });

    // Set first step as current
    if (workflow.steps[0]) {
      setCurrentStep(workflow.steps[0]);
    }
  }, [workflow, updateWorkflow]);

  const completeWorkflow = useCallback(async () => {
    if (!workflow) return;

    // Validate all required steps are completed
    const validation = validateWorkflow();
    if (!validation.isValid) {
      setError(`Cannot complete workflow: ${validation.errors[0]?.message}`);
      return;
    }

    const now = new Date().toISOString();
    const startTime = workflow.startedAt ? new Date(workflow.startedAt) : new Date();
    const duration = Math.round((new Date().getTime() - startTime.getTime()) / 1000 / 60);

    updateWorkflow({
      status: 'completed',
      completedAt: now,
      totalDuration: duration,
      progress: 100,
      currentStepId: null,
    });

    setCurrentStep(null);

    // Trigger haptic feedback
    if ('vibrate' in navigator) {
      navigator.vibrate([200, 100, 200, 100, 200]);
    }
  }, [workflow, updateWorkflow]);

  const pauseWorkflow = useCallback(async () => {
    if (!workflow) return;

    updateWorkflow({ status: 'in_progress' });

    // Pause current step if in progress
    if (currentStep?.status === 'in_progress') {
      await pauseStep(currentStep.id);
    }
  }, [workflow, currentStep, updateWorkflow]);

  const cancelWorkflow = useCallback(async () => {
    if (!workflow) return;

    updateWorkflow({
      status: 'cancelled',
      completedAt: new Date().toISOString(),
      currentStepId: null,
    });

    setCurrentStep(null);
  }, [workflow, updateWorkflow]);

  // Step management
  const startStep = useCallback(
    async (stepId: string) => {
      if (!workflow) return;

      const step = workflow.steps.find((s) => s.id === stepId);
      if (!step) return;

      // Check if step can be started
      if (!canGoToStep(stepId)) {
        setError('Cannot start step: dependencies not met');
        return;
      }

      const updatedSteps = workflow.steps.map((s) =>
        s.id === stepId
          ? { ...s, status: 'in_progress' as const, startedAt: new Date().toISOString() }
          : s
      );

      updateWorkflow({
        steps: updatedSteps,
        currentStepId: stepId,
      });

      setCurrentStep(updatedSteps.find((s) => s.id === stepId) || null);
    },
    [workflow, updateWorkflow]
  );

  const completeStep = useCallback(
    async (stepId: string, data: Record<string, any>, evidence: StepEvidence[]) => {
      if (!workflow) return;

      const step = workflow.steps.find((s) => s.id === stepId);
      if (!step) return;

      const updatedSteps = workflow.steps.map((s) =>
        s.id === stepId
          ? {
              ...s,
              status: 'completed' as const,
              completedAt: new Date().toISOString(),
              data,
              evidence,
            }
          : s
      );

      // Find next step
      const nextStep = getNextStep();

      updateWorkflow({
        steps: updatedSteps,
        currentStepId: nextStep?.id || null,
      });

      setCurrentStep(nextStep);

      // Haptic feedback
      if ('vibrate' in navigator) {
        navigator.vibrate(50);
      }
    },
    [workflow, updateWorkflow]
  );

  const skipStep = useCallback(
    async (stepId: string, reason?: string) => {
      if (!workflow) return;

      const step = workflow.steps.find((s) => s.id === stepId);
      if (!step || step.required) return;

      const updatedSteps = workflow.steps.map((s) =>
        s.id === stepId
          ? {
              ...s,
              status: 'skipped' as const,
              completedAt: new Date().toISOString(),
              data: { skipReason: reason },
            }
          : s
      );

      const nextStep = getNextStep();

      updateWorkflow({
        steps: updatedSteps,
        currentStepId: nextStep?.id || null,
      });

      setCurrentStep(nextStep);
    },
    [workflow, updateWorkflow]
  );

  const pauseStep = useCallback(
    async (stepId: string) => {
      if (!workflow) return;

      const updatedSteps = workflow.steps.map((s) =>
        s.id === stepId ? { ...s, status: 'pending' as const } : s
      );

      updateWorkflow({
        steps: updatedSteps,
        currentStepId: null,
      });

      setCurrentStep(null);
    },
    [workflow, updateWorkflow]
  );

  const goToStep = useCallback(
    async (stepId: string) => {
      if (!canGoToStep(stepId)) return;

      await startStep(stepId);
    },
    [startStep]
  );

  // Navigation helpers
  const canGoToStep = useCallback(
    (stepId: string): boolean => {
      if (!workflow) return false;

      const step = workflow.steps.find((s) => s.id === stepId);
      if (!step) return false;

      // Check dependencies
      if (step.dependencies) {
        return step.dependencies.every((depId) => {
          const depStep = workflow.steps.find((s) => s.id === depId);
          return depStep?.status === 'completed';
        });
      }

      return true;
    },
    [workflow]
  );

  const getNextStep = useCallback((): WorkflowStep | null => {
    if (!workflow || !currentStep) return null;

    const currentIndex = workflow.steps.findIndex((s) => s.id === currentStep.id);
    if (currentIndex === -1) return null;

    // Find next incomplete step
    for (let i = currentIndex + 1; i < workflow.steps.length; i++) {
      const step = workflow.steps[i];
      if (step.status === 'pending' && canGoToStep(step.id)) {
        return step;
      }
    }

    return null;
  }, [workflow, currentStep, canGoToStep]);

  const getPreviousStep = useCallback((): WorkflowStep | null => {
    if (!workflow || !currentStep) return null;

    const currentIndex = workflow.steps.findIndex((s) => s.id === currentStep.id);
    if (currentIndex <= 0) return null;

    return workflow.steps[currentIndex - 1];
  }, [workflow, currentStep]);

  // Validation
  const validateWorkflow = useCallback((): WorkflowValidationResult => {
    if (!workflow) {
      return {
        isValid: false,
        errors: [{ stepId: '', message: 'No workflow loaded' }],
        warnings: [],
      };
    }

    const errors: { stepId: string; field?: string; message: string }[] = [];
    const warnings: { stepId: string; message: string }[] = [];

    workflow.steps.forEach((step) => {
      // Check required steps
      if (step.required && step.status !== 'completed') {
        errors.push({
          stepId: step.id,
          message: `Required step "${step.title}" is not completed`,
        });
      }

      // Check evidence requirements
      if (step.status === 'completed' && step.evidenceRequired) {
        if (step.evidenceRequired.photos) {
          const photoEvidence = step.evidence?.filter((e) => e.type === 'photo') || [];
          if (photoEvidence.length < step.evidenceRequired.photos.minimum) {
            errors.push({
              stepId: step.id,
              message: `Step "${step.title}" requires ${step.evidenceRequired.photos.minimum} photos`,
            });
          }
        }

        if (step.evidenceRequired.signature) {
          const signatureEvidence = step.evidence?.find((e) => e.type === 'signature');
          if (!signatureEvidence) {
            errors.push({
              stepId: step.id,
              message: `Step "${step.title}" requires customer signature`,
            });
          }
        }
      }
    });

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }, [workflow]);

  const validateStep = useCallback(
    (stepId: string): boolean => {
      if (!workflow) return false;

      const step = workflow.steps.find((s) => s.id === stepId);
      if (!step) return false;

      // Validate form data
      if (step.formFields) {
        for (const field of step.formFields) {
          const value = step.data?.[field.id];

          if (field.required && (!value || value.toString().trim() === '')) {
            return false;
          }

          // Check validation rules
          if (field.validation) {
            for (const rule of field.validation) {
              if (rule.type === 'custom' && rule.validator && !rule.validator(value)) {
                return false;
              }
            }
          }
        }
      }

      return true;
    },
    [workflow]
  );

  // Data management
  const updateStepData = useCallback(
    (stepId: string, data: Record<string, any>) => {
      if (!workflow) return;

      const updatedSteps = workflow.steps.map((s) =>
        s.id === stepId ? { ...s, data: { ...s.data, ...data } } : s
      );

      updateWorkflow({ steps: updatedSteps });
    },
    [workflow, updateWorkflow]
  );

  const addStepEvidence = useCallback(
    (stepId: string, evidence: StepEvidence) => {
      if (!workflow) return;

      const updatedSteps = workflow.steps.map((s) =>
        s.id === stepId ? { ...s, evidence: [...(s.evidence || []), evidence] } : s
      );

      updateWorkflow({ steps: updatedSteps });
    },
    [workflow, updateWorkflow]
  );

  const removeStepEvidence = useCallback(
    (stepId: string, evidenceId: string) => {
      if (!workflow) return;

      const updatedSteps = workflow.steps.map((s) =>
        s.id === stepId
          ? { ...s, evidence: (s.evidence || []).filter((e) => e.id !== evidenceId) }
          : s
      );

      updateWorkflow({ steps: updatedSteps });
    },
    [workflow, updateWorkflow]
  );

  // Customer interaction
  const setCustomerPresent = useCallback(
    (present: boolean) => {
      updateWorkflow({ customerPresent: present });
    },
    [updateWorkflow]
  );

  const addCustomerSignature = useCallback(
    (signature: StepEvidence) => {
      updateWorkflow({ customerSignature: signature });
    },
    [updateWorkflow]
  );

  const addCustomerFeedback = useCallback(
    (rating: number, comments: string) => {
      updateWorkflow({
        customerFeedback: { rating, comments },
      });
    },
    [updateWorkflow]
  );

  // Sync operations
  const saveWorkflow = useCallback(async () => {
    if (!workflow) return;

    try {
      await apiClient.put(`/field-ops/workflows/${workflow.id}`, workflow);

      updateWorkflow({ syncStatus: 'synced' });
    } catch (err) {
      console.error('Failed to save workflow:', err);
      updateWorkflow({ syncStatus: 'error' });
    }
  }, [workflow, apiClient, updateWorkflow]);

  const syncWithServer = useCallback(async () => {
    await saveWorkflow();
  }, [saveWorkflow]);

  // Initialize
  useEffect(() => {
    loadWorkflow();
  }, [loadWorkflow]);

  // Auto-save interval
  useEffect(() => {
    if (!autoSave || !workflow) return;

    const interval = setInterval(() => {
      if (workflow.syncStatus === 'pending') {
        saveWorkflow();
      }
    }, saveInterval);

    return () => clearInterval(interval);
  }, [autoSave, workflow, saveInterval, saveWorkflow]);

  // Derived values
  const completedSteps = workflow?.steps.filter((s) => s.status === 'completed').length || 0;
  const totalSteps = workflow?.steps.length || 0;
  const progress = workflow?.progress || 0;

  // Calculate estimated time remaining
  const estimatedTimeRemaining =
    workflow?.steps
      .filter((s) => s.status === 'pending')
      .reduce((total, step) => total + step.estimatedDuration, 0) || 0;

  return {
    // State
    workflow,
    currentStep,
    loading,
    error,

    // Progress
    progress,
    completedSteps,
    totalSteps,
    estimatedTimeRemaining,

    // Actions
    startWorkflow,
    completeWorkflow,
    pauseWorkflow,
    cancelWorkflow,

    // Step management
    startStep,
    completeStep,
    skipStep,
    pauseStep,
    goToStep,

    // Navigation
    canGoToStep,
    getNextStep,
    getPreviousStep,

    // Validation
    validateWorkflow,
    validateStep,

    // Data management
    updateStepData,
    addStepEvidence,
    removeStepEvidence,

    // Sync
    saveWorkflow,
    syncWithServer,

    // Customer interaction
    setCustomerPresent,
    addCustomerSignature,
    addCustomerFeedback,
  };
}
