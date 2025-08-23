import { useCallback, useEffect, useState } from 'react';
/**
 * Business workflow management hook for ISP operations
 */

import { getApiClient } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';

import { useOfflineSync } from './useOfflineSync';
import { usePermissions } from './usePermissions';
import { useRealTimeSync } from './useRealTimeSync';

export interface WorkflowStep {
  id: string;
  name: string;
  description?: string;
  type: 'manual' | 'automated' | 'approval' | 'notification';
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  assignedTo?: string;
  assignedRole?: string;
  requiredPermissions?: string[];
  estimatedDuration?: number; // in minutes
  actualDuration?: number;
  startTime?: number;
  endTime?: number;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
  dependencies?: string[];
  conditions?: Array<{
    field: string;
    operator: 'equals' | 'not_equals' | 'contains' | 'greater_than' | 'less_than';
    value: unknown;
  }>;
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  category: 'customer' | 'network' | 'billing' | 'support' | 'admin';
  version: string;
  steps: WorkflowStep[];
  triggers: Array<{
    type: 'manual' | 'scheduled' | 'event';
    event?: string;
    schedule?: string; // cron expression
    conditions?: unknown[];
  }>;
  settings: {
    allowParallel?: boolean;
    maxExecutionTime?: number;
    retryOnFailure?: boolean;
    maxRetries?: number;
    notificationSettings?: {
      onStart?: boolean;
      onComplete?: boolean;
      onFailure?: boolean;
      recipients?: string[];
    };
  };
}

export interface WorkflowInstance {
  id: string;
  definitionId: string;
  name: string;
  status: 'draft' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
  progress: number; // 0-100
  startTime: number;
  endTime?: number;
  createdBy: string;
  tenantId: string;
  context: Record<string, unknown>;
  currentStep?: string;
  completedSteps: string[];
  failedSteps: string[];
  steps: WorkflowStep[];
  logs: Array<{
    timestamp: number;
    level: 'info' | 'warn' | 'error';
    message: string;
    stepId?: string;
    data?: unknown;
  }>;
}

export interface WorkflowState {
  definitions: WorkflowDefinition[];
  instances: WorkflowInstance[];
  activeInstance: WorkflowInstance | null;
  isLoading: boolean;
  error: string | null;
}

export function useBusinessWorkflow() {
  const { user } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const { hasPermission } = usePermissions();
  const { emit, _subscribe } = useRealTimeSync();
  const { queueOperation, _isOnline } = useOfflineSync();

  const [state, setState] = useState<WorkflowState>({
    definitions: [],
    instances: [],
    activeInstance: null,
    isLoading: false,
    error: null,
  });

  // Load workflow definitions
  const loadDefinitions = useCallback(async () => {
    if (!currentTenant?.tenant?.id) {
      return;
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const apiClient = getApiClient();
      const response = await apiClient.request('/api/v1/workflows/definitions', {
        method: 'GET',
      });

      setState((prev) => ({
        ...prev,
        definitions: response.data.definitions || [],
        isLoading: false,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load workflow definitions',
      }));
    }
  }, [currentTenant?.tenant?.id]);

  // Load workflow instances
  const loadInstances = useCallback(async () => {
    if (!currentTenant?.tenant?.id) {
      return;
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const apiClient = getApiClient();
      const response = await apiClient.request('/api/v1/workflows/instances', {
        method: 'GET',
      });

      setState((prev) => ({
        ...prev,
        instances: response.data.instances || [],
        isLoading: false,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load workflows',
      }));
    }
  }, [currentTenant?.tenant?.id]);

  // Create workflow instance
  const createInstance = useCallback(
    async (
      definitionId: string,
      context: Record<string, unknown> = {
        // Implementation pending
      }
    ): Promise<string | null> => {
      if (!user || !currentTenant?.tenant) {
        return null;
      }

      const definition = state.definitions.find((d) => d.id === definitionId);
      if (!definition) {
        setState((prev) => ({ ...prev, error: 'Workflow definition not found' }));
        return null;
      }

      const instance: WorkflowInstance = {
        id: Date.now().toString(),
        definitionId,
        name: `${definition.name} #${Date.now()}`,
        status: 'draft',
        progress: 0,
        startTime: Date.now(),
        createdBy: user.id,
        tenantId: currentTenant.tenant.id,
        context,
        completedSteps: [],
        failedSteps: [],
        steps: [...definition.steps],
        logs: [
          {
            timestamp: Date.now(),
            level: 'info',
            message: 'Workflow instance created',
          },
        ],
      };

      if (_isOnline) {
        // API call would go here
        setState((prev) => ({
          ...prev,
          instances: [...prev.instances, instance],
        }));

        emit('workflow:created', { instanceId: instance.id });
      } else {
        queueOperation('create', `workflows/${instance.id}`, instance);
      }

      return instance.id;
    },
    [user, currentTenant?.tenant, state.definitions, emit, queueOperation]
  );

  // Start workflow instance
  const startInstance = useCallback(
    async (instanceId: string): Promise<boolean> => {
      const instance = state.instances.find((i) => i.id === instanceId);
      if (!instance || instance.status !== 'draft') {
        return false;
      }

      if (_isOnline) {
        setState((prev) => ({
          ...prev,
          instances: prev.instances.map((i) =>
            i.id === instanceId
              ? {
                  ...i,
                  status: 'running',
                  logs: [
                    ...i.logs,
                    {
                      timestamp: Date.now(),
                      level: 'info',
                      message: 'Workflow started',
                    },
                  ],
                }
              : i
          ),
        }));

        emit('workflow:started', { instanceId });
        return true;
      }
      queueOperation('update', `workflows/${instanceId}/start`, {
        // Implementation pending
      });
      return true;
    },
    [state.instances, emit, queueOperation]
  );

  // Complete workflow step
  const completeStep = useCallback(
    async (
      instanceId: string,
      stepId: string,
      output?: Record<string, unknown>
    ): Promise<boolean> => {
      const instance = state.instances.find((i) => i.id === instanceId);
      if (!instance) {
        return false;
      }

      const step = instance.steps.find((s) => s.id === stepId);
      if (!step || step.status !== 'pending') {
        return false;
      }

      // Check permissions
      if (step.requiredPermissions?.some((perm) => !hasPermission(perm))) {
        setState((prev) => ({ ...prev, error: 'Insufficient permissions' }));
        return false;
      }

      const updatedInstance = {
        ...instance,
        completedSteps: [...instance.completedSteps, stepId],
        steps: instance.steps.map((s) =>
          s.id === stepId
            ? {
                ...s,
                status: 'completed' as const,
                endTime: Date.now(),
                output,
              }
            : s
        ),
        logs: [
          ...instance.logs,
          {
            timestamp: Date.now(),
            level: 'info' as const,
            message: `Step "${step.name}" completed`,
            stepId,
            data: output,
          },
        ],
      };

      // Calculate progress
      updatedInstance.progress = Math.round(
        (updatedInstance.completedSteps.length / updatedInstance.steps.length) * 100
      );

      // Check if workflow is complete
      if (updatedInstance.completedSteps.length === updatedInstance.steps.length) {
        updatedInstance.status = 'completed';
        updatedInstance.endTime = Date.now();
      }

      if (_isOnline) {
        setState((prev) => ({
          ...prev,
          instances: prev.instances.map((i) => (i.id === instanceId ? updatedInstance : i)),
        }));

        emit('workflow:step_completed', { instanceId, stepId, output });
      } else {
        queueOperation('update', `workflows/${instanceId}/steps/${stepId}/complete`, {
          output,
        });
      }

      return true;
    },
    [state.instances, hasPermission, emit, queueOperation]
  );

  // Fail workflow step
  const failStep = useCallback(
    async (instanceId: string, stepId: string, error: string): Promise<boolean> => {
      const instance = state.instances.find((i) => i.id === instanceId);
      if (!instance) {
        return false;
      }

      const step = instance.steps.find((s) => s.id === stepId);
      if (!step) {
        return false;
      }

      const updatedInstance = {
        ...instance,
        failedSteps: [...instance.failedSteps, stepId],
        status: 'failed' as const,
        steps: instance.steps.map((s) =>
          s.id === stepId
            ? {
                ...s,
                status: 'failed' as const,
                endTime: Date.now(),
                error,
              }
            : s
        ),
        logs: [
          ...instance.logs,
          {
            timestamp: Date.now(),
            level: 'error' as const,
            message: `Step "${step.name}" failed: ${error}`,
            stepId,
          },
        ],
      };

      if (_isOnline) {
        setState((prev) => ({
          ...prev,
          instances: prev.instances.map((i) => (i.id === instanceId ? updatedInstance : i)),
        }));

        emit('workflow:step_failed', { instanceId, stepId, error });
      } else {
        queueOperation('update', `workflows/${instanceId}/steps/${stepId}/fail`, {
          error,
        });
      }

      return true;
    },
    [state.instances, emit, queueOperation]
  );

  // Get available actions for current user
  const getAvailableActions = useCallback(
    (instanceId: string): WorkflowStep[] => {
      const instance = state.instances.find((i) => i.id === instanceId);
      if (!instance || instance.status !== 'running') {
        return [];
      }

      return instance.steps.filter((step) => {
        // Check if step is ready to execute
        if (step.status !== 'pending') {
          return false;
        }

        // Check dependencies
        if (step.dependencies?.some((dep) => !instance.completedSteps.includes(dep))) {
          return false;
        }

        // Check permissions
        if (step.requiredPermissions?.some((perm) => !hasPermission(perm))) {
          return false;
        }

        // Check role assignment
        if (step.assignedRole && user?.roles && !user.roles.includes(step.assignedRole)) {
          return false;
        }

        return true;
      });
    },
    [state.instances, hasPermission, user?.roles]
  );

  // Real-time workflow updates
  useEffect(() => {
    return _subscribe('workflow:*', (event) => {
      if (event.type === 'workflow:step_completed' || event.type === 'workflow:step_failed') {
        loadInstances();
      }
    });
  }, [_subscribe, loadInstances]);

  // Load definitions and instances on mount
  useEffect(() => {
    loadDefinitions();
    loadInstances();
  }, [loadDefinitions, loadInstances]);

  return {
    // State
    ...state,

    // Actions
    createInstance,
    startInstance,
    completeStep,
    failStep,
    loadDefinitions,
    loadInstances,

    // Utilities
    getAvailableActions,
    setActiveInstance: (instance: WorkflowInstance | null) =>
      setState((prev) => ({ ...prev, activeInstance: instance })),

    // Computed
    runningInstances: state.instances.filter((i) => i.status === 'running'),
    completedInstances: state.instances.filter((i) => i.status === 'completed'),
    failedInstances: state.instances.filter((i) => i.status === 'failed'),
  };
}
