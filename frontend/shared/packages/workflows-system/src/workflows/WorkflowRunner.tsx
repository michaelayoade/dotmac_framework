'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import WorkflowEngine from '../engines/WorkflowEngine';
import { Stepper, StepIndicator, StepContent, Step } from '../stepper';
import type {
  WorkflowInstance,
  WorkflowDefinition,
  WorkflowStep,
  WorkflowEngineConfig,
} from '../types';

interface WorkflowRunnerProps {
  definitionId?: string;
  instanceId?: string;
  definition?: WorkflowDefinition;
  instance?: WorkflowInstance;
  config?: Partial<WorkflowEngineConfig>;
  onComplete?: (instance: WorkflowInstance) => void;
  onError?: (error: string, instance?: WorkflowInstance) => void;
  onStepComplete?: (stepId: string, output: unknown, instance: WorkflowInstance) => void;
  className?: string;

  // UI customization
  theme?: 'default' | 'modern' | 'minimal';
  orientation?: 'horizontal' | 'vertical';
  showProgress?: boolean;
  showStepNumbers?: boolean;
  allowStepNavigation?: boolean;

  // Custom step components
  stepComponents?: Record<string, React.ComponentType<any>>;
}

export function WorkflowRunner({
  definitionId,
  instanceId,
  definition: providedDefinition,
  instance: providedInstance,
  config = {},
  onComplete,
  onError,
  onStepComplete,
  className,
  theme = 'default',
  orientation = 'horizontal',
  showProgress = true,
  showStepNumbers = true,
  allowStepNavigation = false,
  stepComponents = {},
}: WorkflowRunnerProps) {
  const [engine] = useState(() => new WorkflowEngine(config));
  const [currentInstance, setCurrentInstance] = useState<WorkflowInstance | null>(
    providedInstance || null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Subscribe to engine state changes
  useEffect(() => {
    const unsubscribe = engine.subscribe((state) => {
      if (instanceId) {
        const instance = state.instances.find((i) => i.id === instanceId);
        setCurrentInstance(instance || null);
      }
      setIsLoading(state.isLoading || state.isExecuting);
      setError(state.error);
    });

    return unsubscribe;
  }, [engine, instanceId]);

  // Subscribe to workflow events
  useEffect(() => {
    const unsubscribeComplete = engine.on('workflow:completed', (event) => {
      if (event.instanceId === currentInstance?.id && onComplete && currentInstance) {
        onComplete(currentInstance);
      }
    });

    const unsubscribeError = engine.on('workflow:failed', (event) => {
      if (event.instanceId === currentInstance?.id && onError) {
        onError(event.error, currentInstance || undefined);
      }
    });

    const unsubscribeStepComplete = engine.on('workflow:step_completed', (event) => {
      if (event.instanceId === currentInstance?.id && onStepComplete && currentInstance) {
        onStepComplete(event.stepId, event.output, currentInstance);
      }
    });

    return () => {
      unsubscribeComplete();
      unsubscribeError();
      unsubscribeStepComplete();
    };
  }, [engine, currentInstance?.id, onComplete, onError, onStepComplete, currentInstance]);

  // Initialize workflow
  useEffect(() => {
    const initializeWorkflow = async () => {
      try {
        setIsLoading(true);
        setError(null);

        if (providedInstance) {
          setCurrentInstance(providedInstance);
        } else if (instanceId) {
          await engine.loadInstances();
          // Current instance will be set via state subscription
        } else if (definitionId || providedDefinition) {
          // Create new instance
          const definition =
            providedDefinition ||
            (await engine.loadDefinitions()).find((d) => d.id === definitionId);

          if (!definition) {
            throw new Error(`Workflow definition not found: ${definitionId}`);
          }

          const newInstanceId = await engine.createInstance(definition.id, {}, { autoStart: true });
          // Current instance will be set via state subscription
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to initialize workflow';
        setError(errorMessage);
        if (onError) {
          onError(errorMessage);
        }
      } finally {
        setIsLoading(false);
      }
    };

    initializeWorkflow();
  }, [engine, definitionId, instanceId, providedDefinition, providedInstance, onError]);

  // Convert workflow steps to stepper format
  const stepperSteps = useMemo(() => {
    if (!currentInstance) return [];

    return currentInstance.steps.map((step, index) => ({
      id: step.id,
      title: step.name,
      description: step.description,
      component: stepComponents[step.type] || stepComponents[step.id] || DefaultStepComponent,
      canSkip: step.type === 'manual' && !step.requiredPermissions?.length,
      optional: step.conditions?.length > 0,
    }));
  }, [currentInstance, stepComponents]);

  // Calculate current step index
  const currentStepIndex = useMemo(() => {
    if (!currentInstance) return 0;

    const currentStepId =
      currentInstance.currentStep ||
      currentInstance.steps.find((s) => s.status === 'in_progress')?.id ||
      currentInstance.steps.find((s) => s.status === 'pending')?.id;

    if (!currentStepId) return 0;

    return currentInstance.steps.findIndex((s) => s.id === currentStepId);
  }, [currentInstance]);

  // Handle step completion
  const handleStepChange = async (stepIndex: number, stepData: any) => {
    if (!currentInstance) return;

    const step = currentInstance.steps[stepIndex];
    if (!step) return;

    try {
      await engine.executeStep(currentInstance.id, step.id, stepData.data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Step execution failed';
      if (onError) {
        onError(errorMessage, currentInstance);
      }
    }
  };

  const handleWorkflowComplete = (allData: Record<string, unknown>) => {
    if (currentInstance && onComplete) {
      onComplete({
        ...currentInstance,
        context: { ...currentInstance.context, ...allData },
      });
    }
  };

  if (isLoading) {
    return (
      <div className={clsx('workflow-runner loading', className)}>
        <div className='loading-container'>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className='loading-spinner'
          />
          <p>Loading workflow...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={clsx('workflow-runner error', className)}>
        <div className='error-container'>
          <div className='error-icon'>⚠️</div>
          <h3>Workflow Error</h3>
          <p>{error}</p>
          <button onClick={() => window.location.reload()} className='retry-button'>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!currentInstance) {
    return (
      <div className={clsx('workflow-runner empty', className)}>
        <div className='empty-container'>
          <div className='empty-icon'>📋</div>
          <p>No workflow instance found</p>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('workflow-runner', className, `theme-${theme}`)}>
      {/* Workflow Header */}
      <div className='workflow-header'>
        <div className='workflow-info'>
          <h2 className='workflow-title'>{currentInstance.name}</h2>
          <div className='workflow-meta'>
            <span className={`workflow-status status-${currentInstance.status}`}>
              {currentInstance.status}
            </span>
            <span className='workflow-progress'>{currentInstance.progress}% Complete</span>
            {currentInstance.priority !== 'medium' && (
              <span className={`workflow-priority priority-${currentInstance.priority}`}>
                {currentInstance.priority}
              </span>
            )}
          </div>
        </div>

        {showProgress && (
          <div className='workflow-progress-bar'>
            <motion.div
              className='progress-fill'
              initial={{ width: 0 }}
              animate={{ width: `${currentInstance.progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>
        )}
      </div>

      {/* Stepper */}
      <Stepper
        steps={stepperSteps}
        initialStep={currentStepIndex}
        onStepChange={handleStepChange}
        onComplete={handleWorkflowComplete}
        config={{
          orientation,
          theme,
          showNumbers: showStepNumbers,
          showProgress,
          allowBack: allowStepNavigation,
          validateOnNext: true,
        }}
      >
        <StepIndicator
          showLabels={orientation === 'vertical' || stepperSteps.length <= 5}
          compact={stepperSteps.length > 8}
        />

        <StepContent>
          <AnimatePresence mode='wait'>
            {stepperSteps.map((stepDef, index) => {
              const workflowStep = currentInstance.steps[index];
              const StepComponent = stepDef.component;

              return (
                <Step
                  key={stepDef.id}
                  stepId={stepDef.id}
                  onValidate={async (data) => {
                    // Validate step based on its schema or custom validation
                    if (workflowStep?.schema) {
                      // Implement JSON schema validation here
                      return true; // Placeholder
                    }
                    return true;
                  }}
                  onStepComplete={(data) => {
                    if (onStepComplete) {
                      onStepComplete(stepDef.id, data, currentInstance);
                    }
                  }}
                >
                  <StepComponent
                    step={workflowStep}
                    instance={currentInstance}
                    engine={engine}
                    data={workflowStep?.input || {}}
                    onDataChange={(data: unknown) => {
                      // Update step data
                      // This would typically update the engine state
                    }}
                    onComplete={(output: unknown) => {
                      engine.completeStep(currentInstance.id, stepDef.id, output);
                    }}
                    onError={(error: string) => {
                      if (onError) {
                        onError(error, currentInstance);
                      }
                    }}
                  />
                </Step>
              );
            })}
          </AnimatePresence>
        </StepContent>
      </Stepper>

      {/* Workflow Footer */}
      {currentInstance.status === 'running' && (
        <div className='workflow-footer'>
          <div className='workflow-actions'>
            <button
              onClick={() => engine.pauseWorkflow(currentInstance.id)}
              className='action-button secondary'
            >
              Pause
            </button>
            <button
              onClick={() => engine.cancelWorkflow(currentInstance.id)}
              className='action-button danger'
            >
              Cancel
            </button>
          </div>

          <div className='workflow-metrics'>
            {currentInstance.startTime && (
              <span className='metric'>
                Started: {new Date(currentInstance.startTime).toLocaleString()}
              </span>
            )}
            {currentInstance.estimatedCompletion && (
              <span className='metric'>
                ETA: {new Date(currentInstance.estimatedCompletion).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Default step component for unknown step types
interface DefaultStepComponentProps {
  step: WorkflowStep;
  instance: WorkflowInstance;
  engine: WorkflowEngine;
  data: unknown;
  onDataChange: (data: unknown) => void;
  onComplete: (output: unknown) => void;
  onError: (error: string) => void;
}

function DefaultStepComponent({
  step,
  instance,
  engine,
  data,
  onDataChange,
  onComplete,
  onError,
}: DefaultStepComponentProps) {
  const [stepData, setStepData] = useState(data || {});

  const handleComplete = () => {
    try {
      onComplete(stepData);
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Step completion failed');
    }
  };

  return (
    <div className='default-step-component'>
      <div className='step-content'>
        <h3>{step.name}</h3>
        {step.description && <p className='step-description'>{step.description}</p>}

        <div className='step-details'>
          <div className='detail-item'>
            <label>Type:</label>
            <span className='step-type'>{step.type}</span>
          </div>

          {step.assignedTo && (
            <div className='detail-item'>
              <label>Assigned to:</label>
              <span>{step.assignedTo}</span>
            </div>
          )}

          {step.estimatedDuration && (
            <div className='detail-item'>
              <label>Estimated duration:</label>
              <span>{step.estimatedDuration} minutes</span>
            </div>
          )}
        </div>

        {step.input && Object.keys(step.input).length > 0 && (
          <div className='step-input'>
            <h4>Input Data:</h4>
            <pre>{JSON.stringify(step.input, null, 2)}</pre>
          </div>
        )}

        {step.type === 'manual' && (
          <div className='manual-step-actions'>
            <p>This step requires manual completion.</p>
            <button onClick={handleComplete} className='complete-button'>
              Mark as Complete
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default WorkflowRunner;
