import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type {
  WorkflowDefinition,
  WorkflowInstance,
  WorkflowState,
  WorkflowStep,
  WorkflowEvent,
  WorkflowEngineConfig,
  WorkflowTemplate,
  WorkflowFilters,
} from '../types';

// Default configuration
const defaultConfig: WorkflowEngineConfig = {
  enableRealtime: true,
  enableOffline: true,
  persistenceKey: 'dotmac-workflows',
  maxConcurrentInstances: 10,
  maxRetries: 3,
  defaultTimeout: 5 * 60 * 1000, // 5 minutes
  enableApprovals: true,
  enableNotifications: true,
  enableAuditLog: true,
};

// Workflow execution context
interface ExecutionContext {
  instanceId: string;
  userId: string;
  tenantId: string;
  metadata: Record<string, unknown>;
  variables: Record<string, unknown>;
}

class WorkflowEngine {
  private config: WorkflowEngineConfig;
  private eventListeners: Map<string, Set<(event: WorkflowEvent) => void>> = new Map();
  private stepHandlers: Map<
    string,
    (step: WorkflowStep, context: ExecutionContext) => Promise<unknown>
  > = new Map();
  private runningInstances: Map<string, AbortController> = new Map();
  private store: ReturnType<typeof this.createStore>;

  constructor(config: Partial<WorkflowEngineConfig> = {}) {
    this.config = { ...defaultConfig, ...config };
    this.store = this.createStore();
    this.initializeBuiltInHandlers();
  }

  // Create Zustand store
  private createStore() {
    return create<WorkflowState>()(
      subscribeWithSelector((set, get) => ({
        definitions: [],
        instances: [],
        activeInstance: null,
        templates: [],
        isLoading: false,
        isExecuting: false,
        error: null,
        errors: {},
        filters: {},
        searchQuery: '',
        viewMode: 'list' as const,
        selectedItems: [],
        isConnected: false,
        lastUpdate: Date.now(),

        // Actions will be added via methods below
      }))
    );
  }

  // Initialize built-in step handlers
  private initializeBuiltInHandlers() {
    // Form step handler
    this.registerStepHandler('form', async (step: WorkflowStep, context: ExecutionContext) => {
      return new Promise((resolve) => {
        // Form steps are handled by UI components
        // Return pending status to wait for user interaction
        resolve({ status: 'pending', waitingForInput: true });
      });
    });

    // API call step handler
    this.registerStepHandler('api_call', async (step: WorkflowStep, context: ExecutionContext) => {
      const { url, method = 'GET', headers = {}, body } = step.input as any;

      if (!url) {
        throw new Error('API call step requires URL');
      }

      try {
        const response = await fetch(url, {
          method,
          headers: {
            'Content-Type': 'application/json',
            ...headers,
          },
          body: body ? JSON.stringify(body) : undefined,
        });

        if (!response.ok) {
          throw new Error(`API call failed: ${response.status} ${response.statusText}`);
        }

        const result = await response.json();
        return { status: 'completed', data: result };
      } catch (error) {
        throw new Error(
          `API call failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    });

    // Conditional step handler
    this.registerStepHandler(
      'conditional',
      async (step: WorkflowStep, context: ExecutionContext) => {
        if (!step.conditions || step.conditions.length === 0) {
          return { status: 'skipped', reason: 'No conditions specified' };
        }

        const allConditionsMet = step.conditions.every((condition) => {
          const value = this.getContextValue(context.variables, condition.field);
          return this.evaluateCondition(value, condition.operator, condition.value);
        });

        if (allConditionsMet) {
          return { status: 'completed', conditionsMet: true };
        } else {
          return { status: 'skipped', conditionsMet: false };
        }
      }
    );

    // Notification step handler
    this.registerStepHandler(
      'notification',
      async (step: WorkflowStep, context: ExecutionContext) => {
        const { recipients, message, channel = 'email' } = step.input as any;

        if (!recipients || !message) {
          throw new Error('Notification step requires recipients and message');
        }

        // This would integrate with your notification service
        console.log(`Sending ${channel} notification to ${recipients}: ${message}`);

        return {
          status: 'completed',
          notificationSent: true,
          recipients,
          channel,
        };
      }
    );

    // Approval step handler
    this.registerStepHandler('approval', async (step: WorkflowStep, context: ExecutionContext) => {
      return new Promise((resolve) => {
        // Approval steps are handled by UI components
        // Return pending status to wait for approver action
        resolve({ status: 'pending', waitingForApproval: true });
      });
    });
  }

  // Register custom step handler
  registerStepHandler(
    type: string,
    handler: (step: WorkflowStep, context: ExecutionContext) => Promise<unknown>
  ) {
    this.stepHandlers.set(type, handler);
  }

  // Event system
  on(eventType: string, listener: (event: WorkflowEvent) => void) {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, new Set());
    }
    this.eventListeners.get(eventType)!.add(listener);

    // Return unsubscribe function
    return () => {
      const listeners = this.eventListeners.get(eventType);
      if (listeners) {
        listeners.delete(listener);
        if (listeners.size === 0) {
          this.eventListeners.delete(eventType);
        }
      }
    };
  }

  emit(event: WorkflowEvent) {
    const specificListeners = this.eventListeners.get(event.type);
    const wildcardListeners = this.eventListeners.get('*');

    specificListeners?.forEach((listener) => listener(event));
    wildcardListeners?.forEach((listener) => listener(event));
  }

  // Load workflow definitions
  async loadDefinitions(): Promise<WorkflowDefinition[]> {
    this.store.setState({ isLoading: true, error: null });

    try {
      if (this.config.apiBaseUrl) {
        const response = await fetch(`${this.config.apiBaseUrl}/workflows/definitions`);
        if (!response.ok) throw new Error('Failed to load definitions');
        const definitions = await response.json();

        this.store.setState({ definitions, isLoading: false });
        return definitions;
      } else {
        // Return empty array if no API configured
        this.store.setState({ definitions: [], isLoading: false });
        return [];
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load definitions';
      this.store.setState({ error: errorMessage, isLoading: false });
      throw error;
    }
  }

  // Load workflow instances
  async loadInstances(): Promise<WorkflowInstance[]> {
    this.store.setState({ isLoading: true, error: null });

    try {
      if (this.config.apiBaseUrl) {
        const response = await fetch(`${this.config.apiBaseUrl}/workflows/instances`);
        if (!response.ok) throw new Error('Failed to load instances');
        const instances = await response.json();

        this.store.setState({ instances, isLoading: false });
        return instances;
      } else {
        // Return empty array if no API configured
        this.store.setState({ instances: [], isLoading: false });
        return [];
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load instances';
      this.store.setState({ error: errorMessage, isLoading: false });
      throw error;
    }
  }

  // Create workflow instance from definition
  async createInstance(
    definitionId: string,
    context: Record<string, unknown> = {},
    options: { autoStart?: boolean; priority?: 'low' | 'medium' | 'high' | 'urgent' } = {}
  ): Promise<string> {
    const state = this.store.getState();
    const definition = state.definitions.find((d) => d.id === definitionId);

    if (!definition) {
      throw new Error(`Workflow definition ${definitionId} not found`);
    }

    const instanceId = `instance_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const now = Date.now();

    const instance: WorkflowInstance = {
      id: instanceId,
      definitionId,
      name: `${definition.name} #${instanceId.split('_')[1]}`,
      status: 'draft',
      priority: options.priority || 'medium',
      progress: 0,
      startTime: now,
      createdBy: (context.userId as string) || 'system',
      tenantId: (context.tenantId as string) || 'default',
      context,
      completedSteps: [],
      failedSteps: [],
      skippedSteps: [],
      steps: definition.steps.map((step) => ({
        ...step,
        status: 'pending',
        startTime: undefined,
        endTime: undefined,
      })),
      logs: [
        {
          timestamp: now,
          level: 'info',
          message: 'Workflow instance created',
          userId: context.userId as string,
        },
      ],
      metrics: {
        totalSteps: definition.steps.length,
        completedSteps: 0,
        failedSteps: 0,
      },
    };

    this.store.setState((state) => ({
      instances: [...state.instances, instance],
    }));

    this.emit({ type: 'workflow:created', instanceId, definitionId });

    if (options.autoStart || definition.settings.autoStart) {
      await this.startInstance(instanceId);
    }

    return instanceId;
  }

  // Start workflow instance
  async startInstance(instanceId: string): Promise<void> {
    const state = this.store.getState();
    const instance = state.instances.find((i) => i.id === instanceId);

    if (!instance) {
      throw new Error(`Workflow instance ${instanceId} not found`);
    }

    if (instance.status !== 'draft') {
      throw new Error(`Cannot start workflow in ${instance.status} status`);
    }

    // Update instance status
    this.updateInstanceStatus(instanceId, 'running');

    this.emit({ type: 'workflow:started', instanceId });

    // Start execution
    await this.executeWorkflow(instanceId);
  }

  // Execute workflow
  private async executeWorkflow(instanceId: string): Promise<void> {
    const abortController = new AbortController();
    this.runningInstances.set(instanceId, abortController);

    this.store.setState({ isExecuting: true });

    try {
      const state = this.store.getState();
      const instance = state.instances.find((i) => i.id === instanceId);

      if (!instance) {
        throw new Error(`Workflow instance ${instanceId} not found`);
      }

      const definition = state.definitions.find((d) => d.id === instance.definitionId);
      if (!definition) {
        throw new Error(`Workflow definition ${instance.definitionId} not found`);
      }

      // Execute steps in order
      for (const step of instance.steps) {
        if (abortController.signal.aborted) {
          break;
        }

        // Check if step can be executed
        if (!this.canExecuteStep(step, instance)) {
          continue;
        }

        await this.executeStep(instanceId, step.id);
      }

      // Check if workflow is complete
      const updatedState = this.store.getState();
      const updatedInstance = updatedState.instances.find((i) => i.id === instanceId);

      if (updatedInstance && this.isWorkflowComplete(updatedInstance)) {
        this.updateInstanceStatus(instanceId, 'completed');
        this.emit({ type: 'workflow:completed', instanceId });
      }
    } catch (error) {
      this.updateInstanceStatus(instanceId, 'failed');
      this.emit({
        type: 'workflow:failed',
        instanceId,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      this.runningInstances.delete(instanceId);
      this.store.setState({ isExecuting: false });
    }
  }

  // Execute individual step
  async executeStep(instanceId: string, stepId: string, userInput?: unknown): Promise<void> {
    const state = this.store.getState();
    const instance = state.instances.find((i) => i.id === instanceId);

    if (!instance) {
      throw new Error(`Workflow instance ${instanceId} not found`);
    }

    const step = instance.steps.find((s) => s.id === stepId);
    if (!step) {
      throw new Error(`Step ${stepId} not found`);
    }

    // Update step status to in_progress
    this.updateStepStatus(instanceId, stepId, 'in_progress');
    this.emit({ type: 'workflow:step_started', instanceId, stepId });

    const executionContext: ExecutionContext = {
      instanceId,
      userId: instance.createdBy,
      tenantId: instance.tenantId,
      metadata: step.metadata || {},
      variables: { ...instance.context, userInput },
    };

    try {
      const handler = this.stepHandlers.get(step.type);

      if (!handler) {
        throw new Error(`No handler registered for step type: ${step.type}`);
      }

      const result = await handler(step, executionContext);

      // Handle different result types
      if (result && typeof result === 'object' && 'status' in result) {
        const { status, ...output } = result as any;

        if (status === 'pending') {
          // Step is waiting for external input
          return;
        } else if (status === 'completed') {
          this.updateStepStatus(instanceId, stepId, 'completed', output);
          this.emit({ type: 'workflow:step_completed', instanceId, stepId, output });
        } else if (status === 'skipped') {
          this.updateStepStatus(instanceId, stepId, 'skipped', output);
        }
      } else {
        // Default to completed with result as output
        this.updateStepStatus(instanceId, stepId, 'completed', result);
        this.emit({ type: 'workflow:step_completed', instanceId, stepId, output: result });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.updateStepStatus(instanceId, stepId, 'failed', { error: errorMessage });
      this.emit({ type: 'workflow:step_failed', instanceId, stepId, error: errorMessage });

      // Handle retry logic
      if (step.maxRetries && (step.retryCount || 0) < step.maxRetries) {
        // Implement retry logic here
      }
    }
  }

  // Helper methods
  private canExecuteStep(step: WorkflowStep, instance: WorkflowInstance): boolean {
    // Check if step is already completed, failed, or skipped
    if (['completed', 'failed', 'skipped'].includes(step.status)) {
      return false;
    }

    // Check dependencies
    if (step.dependencies) {
      return step.dependencies.every((dep) => instance.completedSteps.includes(dep));
    }

    return true;
  }

  private isWorkflowComplete(instance: WorkflowInstance): boolean {
    return instance.steps.every((step) => ['completed', 'skipped'].includes(step.status));
  }

  private updateInstanceStatus(instanceId: string, status: WorkflowInstance['status']) {
    this.store.setState((state) => ({
      instances: state.instances.map((instance) =>
        instance.id === instanceId
          ? {
              ...instance,
              status,
              endTime: ['completed', 'failed', 'cancelled'].includes(status)
                ? Date.now()
                : instance.endTime,
              progress: status === 'completed' ? 100 : instance.progress,
            }
          : instance
      ),
    }));
  }

  private updateStepStatus(
    instanceId: string,
    stepId: string,
    status: WorkflowStep['status'],
    output?: unknown
  ) {
    const now = Date.now();

    this.store.setState((state) => ({
      instances: state.instances.map((instance) =>
        instance.id === instanceId
          ? {
              ...instance,
              steps: instance.steps.map((step) =>
                step.id === stepId
                  ? {
                      ...step,
                      status,
                      endTime: ['completed', 'failed', 'skipped'].includes(status)
                        ? now
                        : step.endTime,
                      output: output ? { ...step.output, ...output } : step.output,
                      actualDuration: step.startTime ? now - step.startTime : undefined,
                    }
                  : step
              ),
              completedSteps:
                status === 'completed'
                  ? [...instance.completedSteps, stepId].filter(
                      (id, index, arr) => arr.indexOf(id) === index
                    )
                  : instance.completedSteps.filter((id) => id !== stepId),
              failedSteps:
                status === 'failed'
                  ? [...instance.failedSteps, stepId].filter(
                      (id, index, arr) => arr.indexOf(id) === index
                    )
                  : instance.failedSteps.filter((id) => id !== stepId),
              skippedSteps:
                status === 'skipped'
                  ? [...instance.skippedSteps, stepId].filter(
                      (id, index, arr) => arr.indexOf(id) === index
                    )
                  : instance.skippedSteps.filter((id) => id !== stepId),
              progress: this.calculateProgress(instance.id),
              logs: [
                ...instance.logs,
                {
                  timestamp: now,
                  level: status === 'failed' ? 'error' : 'info',
                  message: `Step "${step.name}" ${status}`,
                  stepId,
                  data: output,
                },
              ],
            }
          : instance
      ),
    }));
  }

  private calculateProgress(instanceId: string): number {
    const state = this.store.getState();
    const instance = state.instances.find((i) => i.id === instanceId);

    if (!instance) return 0;

    const completedCount = instance.steps.filter((s) =>
      ['completed', 'skipped'].includes(s.status)
    ).length;

    return Math.round((completedCount / instance.steps.length) * 100);
  }

  private evaluateCondition(value: unknown, operator: string, expected: unknown): boolean {
    switch (operator) {
      case 'equals':
        return value === expected;
      case 'not_equals':
        return value !== expected;
      case 'contains':
        return String(value).includes(String(expected));
      case 'greater_than':
        return Number(value) > Number(expected);
      case 'less_than':
        return Number(value) < Number(expected);
      case 'exists':
        return value !== null && value !== undefined;
      case 'not_exists':
        return value === null || value === undefined;
      default:
        return false;
    }
  }

  private getContextValue(variables: Record<string, unknown>, path: string): unknown {
    return path
      .split('.')
      .reduce(
        (obj, key) =>
          obj && typeof obj === 'object' && key in obj ? (obj as any)[key] : undefined,
        variables
      );
  }

  // Public API methods
  getState = () => this.store.getState();
  subscribe = this.store.subscribe;

  // Workflow management methods
  pauseWorkflow = (instanceId: string) => this.updateInstanceStatus(instanceId, 'paused');
  cancelWorkflow = (instanceId: string, reason = 'Cancelled by user') => {
    this.updateInstanceStatus(instanceId, 'cancelled');
    this.emit({ type: 'workflow:cancelled', instanceId, reason });
  };

  // Step management methods
  completeStep = (instanceId: string, stepId: string, output?: unknown) =>
    this.executeStep(instanceId, stepId, output);

  skipStep = (instanceId: string, stepId: string, reason = 'Skipped by user') =>
    this.updateStepStatus(instanceId, stepId, 'skipped', { reason });
}

export default WorkflowEngine;
