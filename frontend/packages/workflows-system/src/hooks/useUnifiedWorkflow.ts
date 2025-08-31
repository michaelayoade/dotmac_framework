/**
 * Unified Workflow Hook
 * Consolidates workflow operations using DRY patterns from dotmac_shared
 * Eliminates duplication between useWorkflow, useAutomation, and useBusinessRules
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { standard_exception_handler } from '@dotmac/shared';
import { WorkflowEngine } from '../engines/WorkflowEngine';
import { RuleEngine } from '@dotmac/business-rules-engine';
import type {
  WorkflowDefinition,
  WorkflowInstance,
  WorkflowStepConfig,
  BusinessRule,
  RuleExecutionResult
} from '../types';

export type WorkflowType = 'automation' | 'project' | 'task' | 'business_rule' | 'integration';
export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'completed' | 'failed' | 'cancelled';

interface WorkflowContext {
  portal?: string;
  tenantId: string;
  userId: string;
  variables: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

interface WorkflowOperation {
  type: 'create' | 'update' | 'delete' | 'execute' | 'pause' | 'resume';
  workflowId?: string;
  instanceId?: string;
  data?: any;
}

interface UnifiedWorkflowState {
  definitions: WorkflowDefinition[];
  instances: WorkflowInstance[];
  rules: BusinessRule[];
  executionResults: RuleExecutionResult[];
  isLoading: boolean;
  isExecuting: boolean;
  error: string | null;
}

interface UseUnifiedWorkflowOptions {
  workflowType: WorkflowType;
  tenantId: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseUnifiedWorkflowReturn {
  // State
  state: UnifiedWorkflowState;
  
  // Workflow Definitions
  createDefinition: (definition: Partial<WorkflowDefinition>) => Promise<WorkflowDefinition>;
  updateDefinition: (id: string, updates: Partial<WorkflowDefinition>) => Promise<WorkflowDefinition>;
  deleteDefinition: (id: string) => Promise<void>;
  duplicateDefinition: (id: string) => Promise<WorkflowDefinition>;
  
  // Workflow Instances
  createInstance: (definitionId: string, context: WorkflowContext) => Promise<string>;
  startInstance: (instanceId: string) => Promise<void>;
  pauseInstance: (instanceId: string) => Promise<void>;
  resumeInstance: (instanceId: string) => Promise<void>;
  cancelInstance: (instanceId: string) => Promise<void>;
  
  // Step Operations
  executeStep: (instanceId: string, stepId: string, input?: unknown) => Promise<void>;
  skipStep: (instanceId: string, stepId: string) => Promise<void>;
  retryStep: (instanceId: string, stepId: string) => Promise<void>;
  
  // Rules (for business rule workflows)
  createRule: (rule: Partial<BusinessRule>) => Promise<BusinessRule>;
  updateRule: (id: string, updates: Partial<BusinessRule>) => Promise<BusinessRule>;
  deleteRule: (id: string) => Promise<void>;
  toggleRule: (id: string) => Promise<BusinessRule>;
  testRules: (context: WorkflowContext) => Promise<RuleExecutionResult[]>;
  
  // Utilities
  validateDefinition: (definition: WorkflowDefinition) => Promise<{ isValid: boolean; errors: string[] }>;
  exportDefinition: (id: string) => Promise<Blob>;
  importDefinition: (file: File) => Promise<WorkflowDefinition>;
  refresh: () => Promise<void>;
}

export const useUnifiedWorkflow = standard_exception_handler((
  options: UseUnifiedWorkflowOptions
): UseUnifiedWorkflowReturn => {
  const { workflowType, tenantId, autoRefresh = false, refreshInterval = 30000 } = options;
  const queryClient = useQueryClient();

  // Engines
  const [workflowEngine] = useState(() => new WorkflowEngine({
    enableRealtime: true,
    persistenceKey: `workflows-${workflowType}-${tenantId}`
  }));

  const [ruleEngine] = useState(() => new RuleEngine({
    enableDebug: process.env.NODE_ENV === 'development',
    enableAuditLog: true
  }));

  // Query keys
  const queryKeys = useMemo(() => ({
    definitions: ['workflows', 'definitions', workflowType, tenantId],
    instances: ['workflows', 'instances', workflowType, tenantId],
    rules: ['workflows', 'rules', workflowType, tenantId],
    executions: ['workflows', 'executions', workflowType, tenantId]
  }), [workflowType, tenantId]);

  // Queries
  const definitionsQuery = useQuery({
    queryKey: queryKeys.definitions,
    queryFn: () => workflowEngine.loadDefinitions(),
    refetchInterval: autoRefresh ? refreshInterval : false
  });

  const instancesQuery = useQuery({
    queryKey: queryKeys.instances,
    queryFn: () => workflowEngine.loadInstances(),
    refetchInterval: autoRefresh ? refreshInterval : false
  });

  const rulesQuery = useQuery({
    queryKey: queryKeys.rules,
    queryFn: async () => {
      // Mock API call for rules
      if (workflowType === 'business_rule') {
        return await loadBusinessRules(tenantId);
      }
      return [];
    },
    enabled: workflowType === 'business_rule',
    refetchInterval: autoRefresh ? refreshInterval : false
  });

  // Combined state
  const state: UnifiedWorkflowState = useMemo(() => ({
    definitions: definitionsQuery.data || [],
    instances: instancesQuery.data || [],
    rules: rulesQuery.data || [],
    executionResults: ruleEngine.getAuditLog(),
    isLoading: definitionsQuery.isLoading || instancesQuery.isLoading || rulesQuery.isLoading,
    isExecuting: workflowEngine.getState().isExecuting,
    error: definitionsQuery.error?.message || instancesQuery.error?.message || rulesQuery.error?.message || null
  }), [definitionsQuery, instancesQuery, rulesQuery, ruleEngine, workflowEngine]);

  // Definition mutations
  const createDefinitionMutation = useMutation({
    mutationFn: async (definition: Partial<WorkflowDefinition>) => {
      const newDefinition: WorkflowDefinition = {
        id: `def_${Date.now()}`,
        name: definition.name || 'New Workflow',
        description: definition.description || '',
        version: '1.0.0',
        workflowType,
        tenantId,
        status: 'draft',
        steps: definition.steps || [],
        settings: {
          autoStart: false,
          allowStepNavigation: true,
          showProgress: true,
          persistData: true,
          ...definition.settings
        },
        createdBy: 'current_user',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        ...definition
      };

      // Save via API
      return await saveWorkflowDefinition(newDefinition);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.definitions });
    }
  });

  const updateDefinitionMutation = useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<WorkflowDefinition> }) => {
      const existing = state.definitions.find(d => d.id === id);
      if (!existing) throw new Error('Definition not found');

      const updated = {
        ...existing,
        ...updates,
        updatedAt: new Date().toISOString()
      };

      return await saveWorkflowDefinition(updated);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.definitions });
    }
  });

  const deleteDefinitionMutation = useMutation({
    mutationFn: async (id: string) => {
      await deleteWorkflowDefinition(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.definitions });
    }
  });

  // Instance mutations
  const createInstanceMutation = useMutation({
    mutationFn: async ({ definitionId, context }: { definitionId: string; context: WorkflowContext }) => {
      return await workflowEngine.createInstance(definitionId, context, { autoStart: false });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.instances });
    }
  });

  const startInstanceMutation = useMutation({
    mutationFn: async (instanceId: string) => {
      await workflowEngine.startInstance(instanceId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.instances });
    }
  });

  // Rule mutations (for business rule workflows)
  const createRuleMutation = useMutation({
    mutationFn: async (rule: Partial<BusinessRule>) => {
      const newRule: BusinessRule = {
        id: `rule_${Date.now()}`,
        name: rule.name || 'New Rule',
        description: rule.description || '',
        category: rule.category || 'general',
        status: 'draft',
        priority: rule.priority || 100,
        portalScope: rule.portalScope || ['admin'],
        conditionLogic: rule.conditionLogic || 'all',
        conditions: rule.conditions || [],
        actions: rule.actions || [],
        createdBy: 'current_user',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        tenantId,
        ...rule
      };

      return await saveBusinessRule(newRule);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.rules });
    }
  });

  // Callback functions
  const createDefinition = useCallback(async (definition: Partial<WorkflowDefinition>) => {
    return await createDefinitionMutation.mutateAsync(definition);
  }, [createDefinitionMutation]);

  const updateDefinition = useCallback(async (id: string, updates: Partial<WorkflowDefinition>) => {
    return await updateDefinitionMutation.mutateAsync({ id, updates });
  }, [updateDefinitionMutation]);

  const deleteDefinition = useCallback(async (id: string) => {
    await deleteDefinitionMutation.mutateAsync(id);
  }, [deleteDefinitionMutation]);

  const duplicateDefinition = useCallback(async (id: string) => {
    const existing = state.definitions.find(d => d.id === id);
    if (!existing) throw new Error('Definition not found');

    const duplicate = {
      ...existing,
      id: undefined,
      name: `${existing.name} (Copy)`,
      status: 'draft' as const
    };

    return await createDefinition(duplicate);
  }, [state.definitions, createDefinition]);

  const createInstance = useCallback(async (definitionId: string, context: WorkflowContext) => {
    return await createInstanceMutation.mutateAsync({ definitionId, context });
  }, [createInstanceMutation]);

  const startInstance = useCallback(async (instanceId: string) => {
    await startInstanceMutation.mutateAsync(instanceId);
  }, [startInstanceMutation]);

  const pauseInstance = useCallback(async (instanceId: string) => {
    workflowEngine.pauseWorkflow(instanceId);
    queryClient.invalidateQueries({ queryKey: queryKeys.instances });
  }, [workflowEngine, queryClient, queryKeys.instances]);

  const resumeInstance = useCallback(async (instanceId: string) => {
    await workflowEngine.startInstance(instanceId);
    queryClient.invalidateQueries({ queryKey: queryKeys.instances });
  }, [workflowEngine, queryClient, queryKeys.instances]);

  const cancelInstance = useCallback(async (instanceId: string) => {
    workflowEngine.cancelWorkflow(instanceId);
    queryClient.invalidateQueries({ queryKey: queryKeys.instances });
  }, [workflowEngine, queryClient, queryKeys.instances]);

  const executeStep = useCallback(async (instanceId: string, stepId: string, input?: unknown) => {
    await workflowEngine.executeStep(instanceId, stepId, input);
    queryClient.invalidateQueries({ queryKey: queryKeys.instances });
  }, [workflowEngine, queryClient, queryKeys.instances]);

  const skipStep = useCallback(async (instanceId: string, stepId: string) => {
    workflowEngine.skipStep(instanceId, stepId);
    queryClient.invalidateQueries({ queryKey: queryKeys.instances });
  }, [workflowEngine, queryClient, queryKeys.instances]);

  const retryStep = useCallback(async (instanceId: string, stepId: string) => {
    await workflowEngine.executeStep(instanceId, stepId);
    queryClient.invalidateQueries({ queryKey: queryKeys.instances });
  }, [workflowEngine, queryClient, queryKeys.instances]);

  const createRule = useCallback(async (rule: Partial<BusinessRule>) => {
    return await createRuleMutation.mutateAsync(rule);
  }, [createRuleMutation]);

  const updateRule = useCallback(async (id: string, updates: Partial<BusinessRule>) => {
    const existing = state.rules.find(r => r.id === id);
    if (!existing) throw new Error('Rule not found');

    const updated = {
      ...existing,
      ...updates,
      updatedAt: new Date().toISOString()
    };

    const result = await saveBusinessRule(updated);
    queryClient.invalidateQueries({ queryKey: queryKeys.rules });
    return result;
  }, [state.rules, queryClient, queryKeys.rules]);

  const deleteRule = useCallback(async (id: string) => {
    await deleteBusinessRule(id);
    queryClient.invalidateQueries({ queryKey: queryKeys.rules });
  }, [queryClient, queryKeys.rules]);

  const toggleRule = useCallback(async (id: string) => {
    const rule = state.rules.find(r => r.id === id);
    if (!rule) throw new Error('Rule not found');

    return await updateRule(id, {
      status: rule.status === 'active' ? 'inactive' : 'active'
    });
  }, [state.rules, updateRule]);

  const testRules = useCallback(async (context: WorkflowContext) => {
    if (workflowType !== 'business_rule') {
      throw new Error('Rule testing only available for business rule workflows');
    }

    const ruleContext = {
      portal: context.portal,
      tenantId: context.tenantId,
      userId: context.userId,
      ...context.variables,
      metadata: context.metadata
    };

    return await ruleEngine.executeRules(state.rules.filter(r => r.status === 'active'), ruleContext);
  }, [workflowType, ruleEngine, state.rules]);

  const validateDefinition = useCallback(async (definition: WorkflowDefinition) => {
    const errors: string[] = [];

    if (!definition.name?.trim()) {
      errors.push('Workflow name is required');
    }

    if (!definition.steps?.length) {
      errors.push('At least one step is required');
    }

    // Validate steps
    definition.steps?.forEach((step, index) => {
      if (!step.name?.trim()) {
        errors.push(`Step ${index + 1}: Name is required`);
      }

      if (!step.type) {
        errors.push(`Step ${index + 1}: Type is required`);
      }
    });

    return {
      isValid: errors.length === 0,
      errors
    };
  }, []);

  const exportDefinition = useCallback(async (id: string) => {
    const definition = state.definitions.find(d => d.id === id);
    if (!definition) throw new Error('Definition not found');

    const data = JSON.stringify(definition, null, 2);
    return new Blob([data], { type: 'application/json' });
  }, [state.definitions]);

  const importDefinition = useCallback(async (file: File) => {
    const text = await file.text();
    const definition = JSON.parse(text) as WorkflowDefinition;
    
    // Validate and create new definition
    const validation = await validateDefinition(definition);
    if (!validation.isValid) {
      throw new Error(`Invalid workflow definition: ${validation.errors.join(', ')}`);
    }

    return await createDefinition({
      ...definition,
      id: undefined, // Generate new ID
      status: 'draft'
    });
  }, [validateDefinition, createDefinition]);

  const refresh = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.definitions }),
      queryClient.invalidateQueries({ queryKey: queryKeys.instances }),
      queryClient.invalidateQueries({ queryKey: queryKeys.rules })
    ]);
  }, [queryClient, queryKeys]);

  return {
    state,
    createDefinition,
    updateDefinition,
    deleteDefinition,
    duplicateDefinition,
    createInstance,
    startInstance,
    pauseInstance,
    resumeInstance,
    cancelInstance,
    executeStep,
    skipStep,
    retryStep,
    createRule,
    updateRule,
    deleteRule,
    toggleRule,
    testRules,
    validateDefinition,
    exportDefinition,
    importDefinition,
    refresh
  };
});

// Helper functions (would be replaced with actual API calls)
async function saveWorkflowDefinition(definition: WorkflowDefinition): Promise<WorkflowDefinition> {
  // Mock API call
  console.log('Saving workflow definition:', definition);
  return definition;
}

async function deleteWorkflowDefinition(id: string): Promise<void> {
  // Mock API call
  console.log('Deleting workflow definition:', id);
}

async function loadBusinessRules(tenantId: string): Promise<BusinessRule[]> {
  // Mock API call
  console.log('Loading business rules for tenant:', tenantId);
  return [];
}

async function saveBusinessRule(rule: BusinessRule): Promise<BusinessRule> {
  // Mock API call
  console.log('Saving business rule:', rule);
  return rule;
}

async function deleteBusinessRule(id: string): Promise<void> {
  // Mock API call
  console.log('Deleting business rule:', id);
}

export default useUnifiedWorkflow;