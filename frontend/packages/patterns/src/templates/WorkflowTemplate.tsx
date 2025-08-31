/**
 * Workflow Template
 * Step-by-step guided workflow template with validation and conditional logic
 */

import React, { useState, useEffect, useCallback, useMemo, createContext, useContext } from 'react';
import { clsx } from 'clsx';
import { trackPageView, trackAction } from '@dotmac/monitoring/observability';
import { 
  Card, 
  Button, 
  Input, 
  Select, 
  Textarea,
  Checkbox,
  Badge,
  Progress,
  Alert,
  Skeleton,
  DatePicker
} from '@dotmac/primitives';
import { PermissionGuard } from '@dotmac/rbac';
import { withComponentRegistration } from '@dotmac/registry';
import { useRenderProfiler } from '@dotmac/primitives/utils/performance';
import { 
  WorkflowConfig, 
  WorkflowStepConfig, 
  TemplateState, 
  validateTemplateConfig,
  WorkflowConfigSchema
} from '../types/templates';
import {
  ChevronRight,
  ChevronLeft,
  Check,
  AlertCircle,
  Save,
  X,
  FileText,
  Users,
  Settings,
  Play,
  Pause,
  RotateCcw
} from 'lucide-react';

// Workflow Context
interface WorkflowContextValue {
  config: WorkflowConfig;
  currentStep: number;
  stepData: Record<string, any>;
  errors: Record<string, string[]>;
  isValidating: boolean;
  canGoNext: boolean;
  canGoPrevious: boolean;
  totalSteps: number;
  completedSteps: number[];
  goToStep: (step: number) => void;
  nextStep: () => void;
  previousStep: () => void;
  updateStepData: (data: Record<string, any>) => void;
  validateCurrentStep: () => Promise<boolean>;
  saveProgress: () => Promise<void>;
  resetWorkflow: () => void;
  submitWorkflow: () => Promise<void>;
}

const WorkflowContext = createContext<WorkflowContextValue | null>(null);

export function useWorkflow() {
  const context = useContext(WorkflowContext);
  if (!context) {
    throw new Error('useWorkflow must be used within a WorkflowTemplate');
  }
  return context;
}

// Step Icons
const StepIcons = {
  form: FileText,
  review: Users,
  approval: Check,
  action: Play,
  conditional: Settings,
  parallel: Settings
};

// Step Component
interface WorkflowStepProps {
  step: WorkflowStepConfig;
  isActive: boolean;
  isCompleted: boolean;
  stepIndex: number;
  data: Record<string, any>;
  errors: string[];
  onChange: (data: Record<string, any>) => void;
  onValidate?: () => Promise<{ isValid: boolean; errors: string[] }>;
}

function WorkflowStep({ 
  step, 
  isActive, 
  isCompleted, 
  stepIndex, 
  data, 
  errors, 
  onChange,
  onValidate 
}: WorkflowStepProps) {
  const [localData, setLocalData] = useState(data);
  const [localErrors, setLocalErrors] = useState<string[]>([]);
  const [isValidating, setIsValidating] = useState(false);

  useEffect(() => {
    setLocalData(data);
  }, [data]);

  const handleFieldChange = useCallback((fieldKey: string, value: any) => {
    const newData = { ...localData, [fieldKey]: value };
    setLocalData(newData);
    onChange(newData);

    // Clear field-specific errors
    if (localErrors.length > 0) {
      setLocalErrors(prev => prev.filter(error => !error.includes(fieldKey)));
    }
  }, [localData, onChange, localErrors]);

  const validateStep = useCallback(async () => {
    if (!isActive) return true;

    setIsValidating(true);
    const fieldErrors: string[] = [];

    // Basic field validation
    step.fields.forEach(field => {
      const value = localData[field.key];
      
      if (field.required && (!value || value === '')) {
        fieldErrors.push(`${field.label} is required`);
      }

      if (field.validation && value) {
        if (field.validation.min && value.length < field.validation.min) {
          fieldErrors.push(`${field.label} must be at least ${field.validation.min} characters`);
        }
        if (field.validation.max && value.length > field.validation.max) {
          fieldErrors.push(`${field.label} cannot exceed ${field.validation.max} characters`);
        }
        if (field.validation.pattern && !new RegExp(field.validation.pattern).test(value)) {
          fieldErrors.push(`${field.label} format is invalid`);
        }
      }
    });

    // Step-level validation rules
    if (step.validation?.rules) {
      step.validation.rules.forEach(rule => {
        const fieldValue = localData[rule.field];
        let isValid = false;

        switch (rule.operator) {
          case 'equals':
            isValid = fieldValue === rule.value;
            break;
          case 'notEquals':
            isValid = fieldValue !== rule.value;
            break;
          case 'contains':
            isValid = String(fieldValue).includes(rule.value);
            break;
          case 'greaterThan':
            isValid = Number(fieldValue) > Number(rule.value);
            break;
          case 'lessThan':
            isValid = Number(fieldValue) < Number(rule.value);
            break;
          case 'regex':
            isValid = new RegExp(rule.value).test(String(fieldValue));
            break;
        }

        if (!isValid) {
          fieldErrors.push(rule.message);
        }
      });
    }

    // Custom validation function
    if (step.validation?.onValidate) {
      try {
        const customResult = await step.validation.onValidate(localData);
        if (!customResult.isValid) {
          fieldErrors.push(...customResult.errors);
        }
      } catch (error) {
        fieldErrors.push('Validation failed');
      }
    }

    setLocalErrors(fieldErrors);
    setIsValidating(false);
    
    return fieldErrors.length === 0;
  }, [isActive, localData, step, onValidate]);

  const renderField = (field: WorkflowStepConfig['fields'][0]) => {
    const value = localData[field.key] || field.defaultValue || '';
    const hasError = localErrors.some(error => error.includes(field.label));

    const commonProps = {
      id: `${stepIndex}-${field.key}`,
      required: field.required,
      className: hasError ? 'border-red-500' : '',
      'aria-describedby': field.helpText ? `${stepIndex}-${field.key}-help` : undefined
    };

    switch (field.type) {
      case 'text':
      case 'email':
        return (
          <Input
            {...commonProps}
            type={field.type}
            value={value}
            onChange={(e) => handleFieldChange(field.key, e.target.value)}
            placeholder={field.label}
          />
        );

      case 'number':
        return (
          <Input
            {...commonProps}
            type="number"
            value={value}
            onChange={(e) => handleFieldChange(field.key, Number(e.target.value))}
            placeholder={field.label}
            min={field.validation?.min}
            max={field.validation?.max}
          />
        );

      case 'textarea':
        return (
          <Textarea
            {...commonProps}
            value={value}
            onChange={(e) => handleFieldChange(field.key, e.target.value)}
            placeholder={field.label}
            rows={4}
          />
        );

      case 'select':
        return (
          <Select
            {...commonProps}
            value={value}
            onChange={(val) => handleFieldChange(field.key, val)}
          >
            <option value="">Select {field.label}</option>
            {field.options?.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        );

      case 'multiselect':
        return (
          <div className="space-y-2">
            {field.options?.map(option => (
              <label key={option.value} className="flex items-center space-x-2">
                <Checkbox
                  checked={Array.isArray(value) && value.includes(option.value)}
                  onChange={(checked) => {
                    const currentValues = Array.isArray(value) ? value : [];
                    const newValues = checked 
                      ? [...currentValues, option.value]
                      : currentValues.filter(v => v !== option.value);
                    handleFieldChange(field.key, newValues);
                  }}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        );

      case 'boolean':
        return (
          <label className="flex items-center space-x-2">
            <Checkbox
              {...commonProps}
              checked={Boolean(value)}
              onChange={(checked) => handleFieldChange(field.key, checked)}
            />
            <span>{field.label}</span>
          </label>
        );

      case 'date':
        return (
          <DatePicker
            {...commonProps}
            value={value ? new Date(value) : null}
            onChange={(date) => handleFieldChange(field.key, date?.toISOString())}
          />
        );

      case 'file':
        return (
          <Input
            {...commonProps}
            type="file"
            onChange={(e) => {
              const files = Array.from(e.target.files || []);
              handleFieldChange(field.key, files);
            }}
            multiple={Array.isArray(field.validation?.max)}
          />
        );

      default:
        return null;
    }
  };

  if (!isActive && !isCompleted) {
    return null;
  }

  return (
    <div className={clsx('space-y-6', !isActive && 'opacity-50')}>
      {/* Step Header */}
      <div className="flex items-center space-x-3">
        <div className={clsx(
          'flex h-8 w-8 items-center justify-center rounded-full',
          isCompleted ? 'bg-green-100 text-green-800' : 
          isActive ? 'bg-blue-100 text-blue-800' : 
          'bg-gray-100 text-gray-400'
        )}>
          {isCompleted ? (
            <Check className="h-5 w-5" />
          ) : (
            <span className="text-sm font-medium">{stepIndex + 1}</span>
          )}
        </div>
        <div>
          <h3 className="text-lg font-medium">{step.title}</h3>
          {step.description && (
            <p className="text-sm text-gray-500">{step.description}</p>
          )}
        </div>
      </div>

      {/* Step Content */}
      {isActive && (
        <div className="space-y-4">
          {step.fields.map(field => (
            <div key={field.key} className="space-y-1">
              <label 
                htmlFor={`${stepIndex}-${field.key}`}
                className="block text-sm font-medium"
              >
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              
              {renderField(field)}
              
              {field.helpText && (
                <p 
                  id={`${stepIndex}-${field.key}-help`}
                  className="text-xs text-gray-500"
                >
                  {field.helpText}
                </p>
              )}
            </div>
          ))}

          {/* Step Actions */}
          {step.actions.length > 0 && (
            <div className="flex space-x-2 pt-4">
              {step.actions.map(action => (
                <Button
                  key={action.key}
                  variant={action.variant}
                  disabled={action.disabled}
                  onClick={action.onClick}
                  className="flex items-center space-x-2"
                >
                  {action.icon && <span className="w-4 h-4" />}
                  <span>{action.label}</span>
                </Button>
              ))}
            </div>
          )}

          {/* Validation Errors */}
          {(localErrors.length > 0 || errors.length > 0) && (
            <Alert variant="destructive" className="mt-4">
              <AlertCircle className="h-4 w-4" />
              <div>
                <h4 className="font-medium">Please correct the following errors:</h4>
                <ul className="mt-2 list-disc list-inside text-sm">
                  {[...localErrors, ...errors].map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </div>
            </Alert>
          )}

          {isValidating && (
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <Skeleton className="h-4 w-4 rounded-full" />
              <span>Validating...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Progress Indicator
interface WorkflowProgressProps {
  currentStep: number;
  totalSteps: number;
  completedSteps: number[];
  steps: WorkflowStepConfig[];
  allowStepNavigation: boolean;
  onStepClick?: (step: number) => void;
}

function WorkflowProgress({ 
  currentStep, 
  totalSteps, 
  completedSteps, 
  steps, 
  allowStepNavigation, 
  onStepClick 
}: WorkflowProgressProps) {
  const progressPercentage = (completedSteps.length / totalSteps) * 100;

  return (
    <div className="space-y-4">
      {/* Progress Bar */}
      <div>
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Progress</span>
          <span>{completedSteps.length} of {totalSteps} completed</span>
        </div>
        <Progress value={progressPercentage} className="h-2" />
      </div>

      {/* Step Indicators */}
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = completedSteps.includes(index);
          const isCurrent = currentStep === index;
          const isClickable = allowStepNavigation && onStepClick;
          const StepIcon = StepIcons[step.type] || FileText;

          return (
            <div key={step.id} className="flex flex-col items-center space-y-1">
              <button
                type="button"
                disabled={!isClickable}
                onClick={() => isClickable && onStepClick(index)}
                className={clsx(
                  'flex h-10 w-10 items-center justify-center rounded-full transition-colors',
                  isCompleted && 'bg-green-100 text-green-800',
                  isCurrent && !isCompleted && 'bg-blue-100 text-blue-800 ring-2 ring-blue-500 ring-offset-2',
                  !isCurrent && !isCompleted && 'bg-gray-100 text-gray-400',
                  isClickable && 'hover:bg-opacity-80 cursor-pointer',
                  !isClickable && 'cursor-default'
                )}
              >
                {isCompleted ? (
                  <Check className="h-5 w-5" />
                ) : (
                  <StepIcon className="h-5 w-5" />
                )}
              </button>
              
              <div className="text-center">
                <p className={clsx(
                  'text-xs font-medium',
                  isCurrent ? 'text-blue-800' : 'text-gray-600'
                )}>
                  {step.title}
                </p>
                {step.required && (
                  <Badge variant="secondary" className="text-xs mt-1">
                    Required
                  </Badge>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Main Workflow Template
interface WorkflowTemplateProps {
  config: WorkflowConfig;
  className?: string;
  onStepChange?: (step: number, data: Record<string, any>) => void;
  onComplete?: (data: Record<string, any>) => Promise<void>;
  onCancel?: () => void;
  initialData?: Record<string, any>;
}

function WorkflowTemplateImpl({
  config,
  className = '',
  onStepChange,
  onComplete,
  onCancel,
  initialData = {}
}: WorkflowTemplateProps) {
  // Validate configuration
  const validation = validateTemplateConfig(WorkflowConfigSchema, config);
  if (!validation.isValid) {
    throw new Error(`Invalid workflow configuration: ${validation.errors?.join(', ')}`);
  }

  const validatedConfig = validation.data!;
  
  // Performance monitoring
  useRenderProfiler('WorkflowTemplate', { 
    stepsCount: validatedConfig.steps.length,
    autoSave: validatedConfig.autoSave
  });

  // State management
  const [currentStep, setCurrentStep] = useState(0);
  const [stepData, setStepData] = useState<Record<string, any>>(initialData);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [isValidating, setIsValidating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  // Auto-save functionality
  useEffect(() => {
    if (!validatedConfig.autoSave || !validatedConfig.autoSaveInterval) return;

    const interval = setInterval(async () => {
      if (Object.keys(stepData).length > 0) {
        await saveProgress();
      }
    }, validatedConfig.autoSaveInterval);

    return () => clearInterval(interval);
  }, [stepData, validatedConfig.autoSave, validatedConfig.autoSaveInterval]);

  // Observability tracking
  useEffect(() => {
    const event = new CustomEvent('ui.workflow.start', {
      detail: {
        workflow: validatedConfig.title,
        totalSteps: validatedConfig.steps.length,
        timestamp: new Date().toISOString()
      }
    });
    window.dispatchEvent(event);
    try { trackPageView(`workflow-${validatedConfig.title}`, { totalSteps: validatedConfig.steps.length }); } catch {}
  }, [validatedConfig.title, validatedConfig.steps.length]);

  // Navigation logic
  const canGoNext = useMemo(() => {
    const step = validatedConfig.steps[currentStep];
    return !step.required || completedSteps.includes(currentStep) || step.skippable;
  }, [currentStep, completedSteps, validatedConfig.steps]);

  const canGoPrevious = useMemo(() => {
    return currentStep > 0 && validatedConfig.allowStepNavigation;
  }, [currentStep, validatedConfig.allowStepNavigation]);

  const validateCurrentStep = useCallback(async (): Promise<boolean> => {
    const step = validatedConfig.steps[currentStep];
    if (!step) return false;

    setIsValidating(true);
    const stepErrors: string[] = [];
    const currentStepData = stepData[currentStep] || {};

    // Field validation
    for (const field of step.fields) {
      const value = currentStepData[field.key];
      
      if (field.required && (!value || value === '')) {
        stepErrors.push(`${field.label} is required`);
      }
    }

    // Custom validation
    if (step.validation?.onValidate) {
      try {
        const result = await step.validation.onValidate(currentStepData);
        if (!result.isValid) {
          stepErrors.push(...result.errors);
        }
      } catch (error) {
        stepErrors.push('Validation failed');
      }
    }

    setErrors(prev => ({ ...prev, [currentStep]: stepErrors }));
    setIsValidating(false);

    const isValid = stepErrors.length === 0;
    if (isValid && !completedSteps.includes(currentStep)) {
      setCompletedSteps(prev => [...prev, currentStep]);
    }

    return isValid;
  }, [currentStep, stepData, completedSteps, validatedConfig.steps]);

  const goToStep = useCallback((step: number) => {
    if (step >= 0 && step < validatedConfig.steps.length) {
      setCurrentStep(step);
      onStepChange?.(step, stepData);
      
      const event = new CustomEvent('ui.workflow.step', {
        detail: {
          step: step + 1,
          stepId: validatedConfig.steps[step].id,
          timestamp: new Date().toISOString()
        }
      });
      window.dispatchEvent(event);
      try { trackAction('workflow_step', 'navigation', { step: step + 1 }); } catch {}
    }
  }, [validatedConfig.steps, stepData, onStepChange]);

  const nextStep = useCallback(async () => {
    const isValid = await validateCurrentStep();
    if (!isValid && validatedConfig.steps[currentStep].required) return;

    const step = validatedConfig.steps[currentStep];
    let nextStepIndex = currentStep + 1;

    // Handle conditional steps
    if (step.condition) {
      const fieldValue = stepData[currentStep]?.[step.condition.field];
      let conditionMet = false;

      switch (step.condition.operator) {
        case 'equals':
          conditionMet = fieldValue === step.condition.value;
          break;
        case 'notEquals':
          conditionMet = fieldValue !== step.condition.value;
          break;
        case 'contains':
          conditionMet = String(fieldValue).includes(step.condition.value);
          break;
        case 'greaterThan':
          conditionMet = Number(fieldValue) > Number(step.condition.value);
          break;
        case 'lessThan':
          conditionMet = Number(fieldValue) < Number(step.condition.value);
          break;
      }

      if (conditionMet && step.condition.nextStep) {
        const conditionalStepIndex = validatedConfig.steps.findIndex(s => s.id === step.condition!.nextStep);
        if (conditionalStepIndex !== -1) {
          nextStepIndex = conditionalStepIndex;
        }
      }
    }

    if (nextStepIndex < validatedConfig.steps.length) {
      goToStep(nextStepIndex);
    } else {
      // Workflow complete
      await submitWorkflow();
    }
  }, [currentStep, validateCurrentStep, stepData, validatedConfig.steps, goToStep]);

  const previousStep = useCallback(() => {
    if (canGoPrevious) {
      goToStep(currentStep - 1);
    }
  }, [canGoPrevious, currentStep, goToStep]);

  const updateStepData = useCallback((data: Record<string, any>) => {
    setStepData(prev => ({
      ...prev,
      [currentStep]: { ...prev[currentStep], ...data }
    }));
  }, [currentStep]);

  const saveProgress = useCallback(async () => {
    if (isSaving) return;
    
    setIsSaving(true);
    try {
      // Save to localStorage as fallback
      localStorage.setItem(`workflow-${validatedConfig.title}`, JSON.stringify({
        currentStep,
        stepData,
        completedSteps,
        timestamp: new Date().toISOString()
      }));
      
      setLastSaved(new Date());
      
      const event = new CustomEvent('ui.workflow.save', {
        detail: {
          workflow: validatedConfig.title,
          step: currentStep + 1,
          timestamp: new Date().toISOString()
        }
      });
      window.dispatchEvent(event);
      try { trackAction('workflow_save', 'progress', { step: currentStep + 1 }); } catch {}
    } catch (error) {
      console.error('Failed to save workflow progress:', error);
    } finally {
      setIsSaving(false);
    }
  }, [currentStep, stepData, completedSteps, validatedConfig.title, isSaving]);

  const resetWorkflow = useCallback(() => {
    setCurrentStep(0);
    setStepData(initialData);
    setCompletedSteps([]);
    setErrors({});
    localStorage.removeItem(`workflow-${validatedConfig.title}`);
    
    const event = new CustomEvent('ui.workflow.reset', {
      detail: {
        workflow: validatedConfig.title,
        timestamp: new Date().toISOString()
      }
    });
    window.dispatchEvent(event);
    try { trackAction('workflow_reset', 'action'); } catch {}
  }, [initialData, validatedConfig.title]);

  const submitWorkflow = useCallback(async () => {
    try {
      const finalData = Object.values(stepData).reduce((acc, step) => ({ ...acc, ...step }), {});
      await onComplete?.(finalData);
      
      const event = new CustomEvent('ui.workflow.complete', {
        detail: {
          workflow: validatedConfig.title,
          totalSteps: validatedConfig.steps.length,
          completedSteps: completedSteps.length,
          timestamp: new Date().toISOString()
        }
      });
      window.dispatchEvent(event);
      try { trackAction('workflow_complete', 'success', { totalSteps: validatedConfig.steps.length }); } catch {}
      
      // Clear saved progress
      localStorage.removeItem(`workflow-${validatedConfig.title}`);
    } catch (error) {
      console.error('Failed to submit workflow:', error);
    }
  }, [stepData, onComplete, validatedConfig.title, validatedConfig.steps.length, completedSteps.length]);

  // Context value
  const contextValue: WorkflowContextValue = {
    config: validatedConfig,
    currentStep,
    stepData,
    errors,
    isValidating,
    canGoNext,
    canGoPrevious,
    totalSteps: validatedConfig.steps.length,
    completedSteps,
    goToStep,
    nextStep,
    previousStep,
    updateStepData,
    validateCurrentStep,
    saveProgress,
    resetWorkflow,
    submitWorkflow
  };

  const currentStepConfig = validatedConfig.steps[currentStep];

  return (
    <WorkflowContext.Provider value={contextValue}>
      <div className={clsx('max-w-4xl mx-auto space-y-8', className)}>
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold">{validatedConfig.title}</h1>
          {validatedConfig.description && (
            <p className="text-gray-600">{validatedConfig.description}</p>
          )}
        </div>

        {/* Progress Indicator */}
        {validatedConfig.showProgress && (
          <Card className="p-6">
            <WorkflowProgress
              currentStep={currentStep}
              totalSteps={validatedConfig.steps.length}
              completedSteps={completedSteps}
              steps={validatedConfig.steps}
              allowStepNavigation={validatedConfig.allowStepNavigation}
              onStepClick={validatedConfig.allowStepNavigation ? goToStep : undefined}
            />
          </Card>
        )}

        {/* Current Step */}
        <Card className="p-6">
          <WorkflowStep
            step={currentStepConfig}
            isActive={true}
            isCompleted={completedSteps.includes(currentStep)}
            stepIndex={currentStep}
            data={stepData[currentStep] || {}}
            errors={errors[currentStep] || []}
            onChange={updateStepData}
            onValidate={validateCurrentStep}
          />
        </Card>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {canGoPrevious && (
              <Button
                variant="outline"
                onClick={previousStep}
                className="flex items-center space-x-2"
              >
                <ChevronLeft className="h-4 w-4" />
                <span>Previous</span>
              </Button>
            )}
            
            {onCancel && (
              <Button
                variant="ghost"
                onClick={onCancel}
                className="flex items-center space-x-2"
              >
                <X className="h-4 w-4" />
                <span>Cancel</span>
              </Button>
            )}
          </div>

          <div className="flex items-center space-x-4">
            {/* Auto-save indicator */}
            {validatedConfig.persistData && lastSaved && (
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <Save className="h-4 w-4" />
                <span>Saved {lastSaved.toLocaleTimeString()}</span>
              </div>
            )}

            {/* Manual save */}
            {validatedConfig.persistData && (
              <Button
                variant="ghost"
                onClick={saveProgress}
                disabled={isSaving}
                className="flex items-center space-x-2"
              >
                <Save className={clsx('h-4 w-4', isSaving && 'animate-spin')} />
                <span>{isSaving ? 'Saving...' : 'Save'}</span>
              </Button>
            )}

            {/* Reset */}
            <Button
              variant="ghost"
              onClick={resetWorkflow}
              className="flex items-center space-x-2"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Reset</span>
            </Button>

            {/* Next/Complete */}
            <Button
              onClick={nextStep}
              disabled={isValidating || (!canGoNext && currentStepConfig.required)}
              className="flex items-center space-x-2"
            >
              <span>
                {currentStep === validatedConfig.steps.length - 1 ? 'Complete' : 'Next'}
              </span>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </WorkflowContext.Provider>
  );
}

export const WorkflowTemplate = withComponentRegistration(WorkflowTemplateImpl, {
  name: 'WorkflowTemplate',
  category: 'template',
  portal: 'shared',
  version: '1.0.0',
  description: 'Step-by-step workflow template with validation and conditional logic',
});

export default WorkflowTemplate;
