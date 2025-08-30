import { useEffect, useState, useMemo, useCallback } from 'react';
import WorkflowEngine from '../../engines/WorkflowEngine';
import type {
  WorkflowInstance,
  WorkflowDefinition,
  WorkflowEngineConfig,
  WorkflowEvent,
  WorkflowFilters
} from '../../types';

interface UseWorkflowOptions {
  config?: Partial<WorkflowEngineConfig>;
  autoLoad?: boolean;
  filters?: WorkflowFilters;
}

interface UseWorkflowReturn {
  // State
  instances: WorkflowInstance[];
  definitions: WorkflowDefinition[];
  activeInstance: WorkflowInstance | null;
  isLoading: boolean;
  isExecuting: boolean;
  error: string | null;

  // Computed
  runningInstances: WorkflowInstance[];
  completedInstances: WorkflowInstance[];
  failedInstances: WorkflowInstance[];
  filteredInstances: WorkflowInstance[];

  // Actions
  createInstance: (definitionId: string, context?: Record<string, unknown>) => Promise<string | null>;
  startInstance: (instanceId: string) => Promise<void>;
  pauseInstance: (instanceId: string) => void;
  cancelInstance: (instanceId: string, reason?: string) => void;
  completeStep: (instanceId: string, stepId: string, output?: unknown) => Promise<void>;
  skipStep: (instanceId: string, stepId: string, reason?: string) => void;

  // Data loading
  loadDefinitions: () => Promise<WorkflowDefinition[]>;
  loadInstances: () => Promise<WorkflowInstance[]>;
  refreshData: () => Promise<void>;

  // Instance management
  setActiveInstance: (instance: WorkflowInstance | null) => void;
  getInstanceById: (instanceId: string) => WorkflowInstance | undefined;
  getDefinitionById: (definitionId: string) => WorkflowDefinition | undefined;

  // Event handling
  on: (event: string, handler: (event: WorkflowEvent) => void) => () => void;

  // Engine reference
  engine: WorkflowEngine;
}

// Global engine instance (singleton pattern)
let globalEngine: WorkflowEngine | null = null;

export function useWorkflow(options: UseWorkflowOptions = {}): UseWorkflowReturn {
  const { config = {}, autoLoad = true, filters = {} } = options;

  // Initialize engine
  const engine = useMemo(() => {
    if (!globalEngine) {
      globalEngine = new WorkflowEngine(config);
    }
    return globalEngine;
  }, [config]);

  // Subscribe to engine state
  const [state, setState] = useState(engine.getState());

  useEffect(() => {
    const unsubscribe = engine.subscribe((newState) => {
      setState(newState);
    });

    return unsubscribe;
  }, [engine]);

  // Auto-load data
  useEffect(() => {
    if (autoLoad) {
      engine.loadDefinitions();
      engine.loadInstances();
    }
  }, [engine, autoLoad]);

  // Computed values
  const runningInstances = useMemo(() =>
    state.instances.filter(i => i.status === 'running'),
    [state.instances]
  );

  const completedInstances = useMemo(() =>
    state.instances.filter(i => i.status === 'completed'),
    [state.instances]
  );

  const failedInstances = useMemo(() =>
    state.instances.filter(i => i.status === 'failed'),
    [state.instances]
  );

  const filteredInstances = useMemo(() => {
    let filtered = state.instances;

    if (filters.status?.length) {
      filtered = filtered.filter(i => filters.status!.includes(i.status));
    }

    if (filters.category?.length) {
      filtered = filtered.filter(i => {
        const definition = state.definitions.find(d => d.id === i.definitionId);
        return definition && filters.category!.includes(definition.category);
      });
    }

    if (filters.priority?.length) {
      filtered = filtered.filter(i => filters.priority!.includes(i.priority));
    }

    if (filters.assignedTo?.length) {
      filtered = filtered.filter(i => {
        const currentStep = i.steps.find(s => s.status === 'in_progress');
        return currentStep && filters.assignedTo!.includes(currentStep.assignedTo || '');
      });
    }

    if (filters.dateRange) {
      filtered = filtered.filter(i =>
        i.startTime >= filters.dateRange!.start &&
        i.startTime <= filters.dateRange!.end
      );
    }

    if (filters.tags?.length) {
      filtered = filtered.filter(i => {
        const definition = state.definitions.find(d => d.id === i.definitionId);
        return definition?.tags?.some(tag => filters.tags!.includes(tag));
      });
    }

    return filtered;
  }, [state.instances, state.definitions, filters]);

  // Actions
  const createInstance = useCallback(async (
    definitionId: string,
    context: Record<string, unknown> = {}
  ) => {
    try {
      return await engine.createInstance(definitionId, context);
    } catch (error) {
      console.error('Failed to create workflow instance:', error);
      return null;
    }
  }, [engine]);

  const startInstance = useCallback(async (instanceId: string) => {
    try {
      await engine.startInstance(instanceId);
    } catch (error) {
      console.error('Failed to start workflow instance:', error);
      throw error;
    }
  }, [engine]);

  const pauseInstance = useCallback((instanceId: string) => {
    engine.pauseWorkflow(instanceId);
  }, [engine]);

  const cancelInstance = useCallback((instanceId: string, reason = 'Cancelled by user') => {
    engine.cancelWorkflow(instanceId, reason);
  }, [engine]);

  const completeStep = useCallback(async (
    instanceId: string,
    stepId: string,
    output?: unknown
  ) => {
    try {
      await engine.executeStep(instanceId, stepId, output);
    } catch (error) {
      console.error('Failed to complete step:', error);
      throw error;
    }
  }, [engine]);

  const skipStep = useCallback((
    instanceId: string,
    stepId: string,
    reason = 'Skipped by user'
  ) => {
    engine.skipStep(instanceId, stepId, reason);
  }, [engine]);

  const loadDefinitions = useCallback(async () => {
    try {
      return await engine.loadDefinitions();
    } catch (error) {
      console.error('Failed to load workflow definitions:', error);
      throw error;
    }
  }, [engine]);

  const loadInstances = useCallback(async () => {
    try {
      return await engine.loadInstances();
    } catch (error) {
      console.error('Failed to load workflow instances:', error);
      throw error;
    }
  }, [engine]);

  const refreshData = useCallback(async () => {
    try {
      await Promise.all([
        engine.loadDefinitions(),
        engine.loadInstances()
      ]);
    } catch (error) {
      console.error('Failed to refresh workflow data:', error);
      throw error;
    }
  }, [engine]);

  const setActiveInstance = useCallback((instance: WorkflowInstance | null) => {
    // Update engine state - this would need to be implemented in the engine
    // For now, we'll just update local state
    setState(prevState => ({
      ...prevState,
      activeInstance: instance
    }));
  }, []);

  const getInstanceById = useCallback((instanceId: string) => {
    return state.instances.find(i => i.id === instanceId);
  }, [state.instances]);

  const getDefinitionById = useCallback((definitionId: string) => {
    return state.definitions.find(d => d.id === definitionId);
  }, [state.definitions]);

  const on = useCallback((event: string, handler: (event: WorkflowEvent) => void) => {
    return engine.on(event, handler);
  }, [engine]);

  return {
    // State
    instances: state.instances,
    definitions: state.definitions,
    activeInstance: state.activeInstance,
    isLoading: state.isLoading,
    isExecuting: state.isExecuting,
    error: state.error,

    // Computed
    runningInstances,
    completedInstances,
    failedInstances,
    filteredInstances,

    // Actions
    createInstance,
    startInstance,
    pauseInstance,
    cancelInstance,
    completeStep,
    skipStep,

    // Data loading
    loadDefinitions,
    loadInstances,
    refreshData,

    // Instance management
    setActiveInstance,
    getInstanceById,
    getDefinitionById,

    // Event handling
    on,

    // Engine reference
    engine,
  };
}

export default useWorkflow;
