'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { StepperConfig, WorkflowStep } from '../types';

// Stepper Context
interface StepperContextValue {
  currentStep: number;
  totalSteps: number;
  steps: StepData[];
  canGoNext: boolean;
  canGoPrevious: boolean;
  isValidating: boolean;
  errors: Record<string, string>;

  // Actions
  nextStep: () => Promise<boolean>;
  previousStep: () => void;
  goToStep: (step: number) => Promise<boolean>;
  setStepData: (step: number, data: unknown, isValid?: boolean) => void;
  setStepError: (step: number, error: string | null) => void;
  validateStep: (step: number) => Promise<boolean>;
  completeStep: (step: number, data?: unknown) => void;

  // Configuration
  config: StepperConfig;
}

interface StepData {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'current' | 'completed' | 'error' | 'skipped';
  data?: unknown;
  isValid: boolean;
  error?: string;
  canSkip?: boolean;
  optional?: boolean;
  component?: React.ComponentType<any>;
}

const StepperContext = createContext<StepperContextValue | null>(null);

export const useStepper = () => {
  const context = useContext(StepperContext);
  if (!context) {
    throw new Error('useStepper must be used within a StepperProvider');
  }
  return context;
};

// Default stepper configuration
const defaultConfig: StepperConfig = {
  orientation: 'horizontal',
  variant: 'default',
  showNumbers: true,
  showProgress: true,
  allowSkip: false,
  allowBack: true,
  theme: 'default',
  autoAdvance: false,
  validateOnNext: true,
  persistProgress: false,
  colors: {
    active: 'rgb(59 130 246)', // blue-500
    completed: 'rgb(34 197 94)', // green-500
    pending: 'rgb(156 163 175)', // gray-400
    error: 'rgb(239 68 68)', // red-500
  },
};

interface StepperProps {
  children: React.ReactNode;
  steps: Omit<StepData, 'status' | 'isValid'>[];
  config?: Partial<StepperConfig>;
  initialStep?: number;
  onStepChange?: (step: number, stepData: StepData) => void;
  onComplete?: (allData: Record<string, unknown>) => void;
  className?: string;
}

export function Stepper({
  children,
  steps: stepDefinitions,
  config: configOverrides = {},
  initialStep = 0,
  onStepChange,
  onComplete,
  className
}: StepperProps) {
  const config = { ...defaultConfig, ...configOverrides };

  const [currentStep, setCurrentStep] = useState(initialStep);
  const [steps, setSteps] = useState<StepData[]>(() =>
    stepDefinitions.map((step, index) => ({
      ...step,
      status: index === initialStep ? 'current' : 'pending',
      isValid: false,
    }))
  );
  const [isValidating, setIsValidating] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Calculate derived state
  const canGoNext = currentStep < steps.length - 1 && (steps[currentStep]?.isValid || !config.validateOnNext);
  const canGoPrevious = currentStep > 0 && config.allowBack;
  const totalSteps = steps.length;

  // Step navigation
  const goToStep = useCallback(async (targetStep: number): Promise<boolean> => {
    if (targetStep < 0 || targetStep >= steps.length) {
      return false;
    }

    if (targetStep > currentStep) {
      // Moving forward - validate current step if required
      if (config.validateOnNext && !steps[currentStep]?.isValid) {
        setIsValidating(true);
        const isValid = await validateStep(currentStep);
        setIsValidating(false);

        if (!isValid) {
          return false;
        }
      }
    } else if (targetStep < currentStep) {
      // Moving backward - check if allowed
      if (!config.allowBack) {
        return false;
      }
    }

    // Update steps status
    setSteps(prevSteps =>
      prevSteps.map((step, index) => {
        let status: StepData['status'] = 'pending';

        if (index < targetStep) {
          status = 'completed';
        } else if (index === targetStep) {
          status = 'current';
        } else {
          status = 'pending';
        }

        return { ...step, status };
      })
    );

    setCurrentStep(targetStep);

    if (onStepChange) {
      onStepChange(targetStep, steps[targetStep]);
    }

    return true;
  }, [currentStep, steps, config.validateOnNext, config.allowBack, onStepChange]);

  const nextStep = useCallback(async (): Promise<boolean> => {
    if (!canGoNext && currentStep < steps.length - 1) {
      return await goToStep(currentStep + 1);
    }

    // Check if this is the last step and we're completing
    if (currentStep === steps.length - 1) {
      if (onComplete) {
        const allData = steps.reduce((acc, step, index) => {
          acc[step.id] = step.data;
          return acc;
        }, {} as Record<string, unknown>);

        onComplete(allData);
      }
      return true;
    }

    return false;
  }, [canGoNext, currentStep, steps, goToStep, onComplete]);

  const previousStep = useCallback(() => {
    if (canGoPrevious) {
      goToStep(currentStep - 1);
    }
  }, [canGoPrevious, currentStep, goToStep]);

  // Step data management
  const setStepData = useCallback((step: number, data: unknown, isValid = true) => {
    setSteps(prevSteps =>
      prevSteps.map((s, index) =>
        index === step ? { ...s, data, isValid, error: undefined } : s
      )
    );

    // Clear any errors for this step
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[step.toString()];
      return newErrors;
    });
  }, []);

  const setStepError = useCallback((step: number, error: string | null) => {
    setSteps(prevSteps =>
      prevSteps.map((s, index) =>
        index === step ? { ...s, error, isValid: !error, status: error ? 'error' : s.status } : s
      )
    );

    setErrors(prev => ({
      ...prev,
      [step.toString()]: error || ''
    }));
  }, []);

  const validateStep = useCallback(async (step: number): Promise<boolean> => {
    const stepData = steps[step];
    if (!stepData) return false;

    // Custom validation logic can be implemented here
    // For now, just check if step has data and no errors
    const hasData = stepData.data !== undefined;
    const hasError = Boolean(stepData.error);

    return hasData && !hasError;
  }, [steps]);

  const completeStep = useCallback((step: number, data?: unknown) => {
    setSteps(prevSteps =>
      prevSteps.map((s, index) =>
        index === step
          ? {
              ...s,
              data: data !== undefined ? data : s.data,
              status: 'completed',
              isValid: true,
              error: undefined
            }
          : s
      )
    );

    // Auto-advance if enabled
    if (config.autoAdvance && step === currentStep && step < steps.length - 1) {
      setTimeout(() => goToStep(step + 1), 300);
    }
  }, [config.autoAdvance, currentStep, steps.length, goToStep]);

  // Context value
  const contextValue: StepperContextValue = {
    currentStep,
    totalSteps,
    steps,
    canGoNext,
    canGoPrevious,
    isValidating,
    errors,
    nextStep,
    previousStep,
    goToStep,
    setStepData,
    setStepError,
    validateStep,
    completeStep,
    config,
  };

  return (
    <StepperContext.Provider value={contextValue}>
      <div className={clsx('dotmac-stepper', className, {
        'stepper-horizontal': config.orientation === 'horizontal',
        'stepper-vertical': config.orientation === 'vertical',
        [`stepper-${config.variant}`]: config.variant,
        [`stepper-${config.theme}`]: config.theme,
      })}>
        {children}
      </div>
    </StepperContext.Provider>
  );
}

// Step indicator component
interface StepIndicatorProps {
  className?: string;
  showLabels?: boolean;
  compact?: boolean;
}

export function StepIndicator({ className, showLabels = true, compact = false }: StepIndicatorProps) {
  const { steps, currentStep, config, goToStep } = useStepper();

  const getStepColor = (step: StepData, index: number) => {
    switch (step.status) {
      case 'completed':
        return config.colors?.completed || defaultConfig.colors!.completed;
      case 'current':
        return config.colors?.active || defaultConfig.colors!.active;
      case 'error':
        return config.colors?.error || defaultConfig.colors!.error;
      default:
        return config.colors?.pending || defaultConfig.colors!.pending;
    }
  };

  const handleStepClick = async (index: number) => {
    if (index <= currentStep || !config.validateOnNext) {
      await goToStep(index);
    }
  };

  if (config.orientation === 'horizontal') {
    return (
      <div className={clsx('stepper-indicator horizontal', className, { compact })}>
        {config.showProgress && (
          <div className="progress-track">
            <motion.div
              className="progress-fill"
              style={{ backgroundColor: config.colors?.active }}
              initial={{ width: 0 }}
              animate={{ width: `${(currentStep / (steps.length - 1)) * 100}%` }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
            />
          </div>
        )}

        <div className="steps-container">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={clsx('step-item', {
                clickable: index <= currentStep || !config.validateOnNext,
                current: index === currentStep,
                completed: step.status === 'completed',
                error: step.status === 'error',
              })}
              onClick={() => handleStepClick(index)}
            >
              <motion.div
                className="step-circle"
                style={{ borderColor: getStepColor(step, index) }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <AnimatePresence mode="wait">
                  {step.status === 'completed' ? (
                    <motion.div
                      key="check"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      className="step-check"
                      style={{ color: config.colors?.completed }}
                    >
                      ✓
                    </motion.div>
                  ) : step.status === 'error' ? (
                    <motion.div
                      key="error"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      className="step-error"
                      style={{ color: config.colors?.error }}
                    >
                      ✕
                    </motion.div>
                  ) : config.showNumbers ? (
                    <motion.span
                      key="number"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      className="step-number"
                      style={{ color: getStepColor(step, index) }}
                    >
                      {index + 1}
                    </motion.span>
                  ) : null}
                </AnimatePresence>
              </motion.div>

              {showLabels && !compact && (
                <div className="step-label">
                  <div className="step-title" style={{ color: getStepColor(step, index) }}>
                    {step.title}
                  </div>
                  {step.description && (
                    <div className="step-description">
                      {step.description}
                    </div>
                  )}
                </div>
              )}

              {index < steps.length - 1 && (
                <div className="step-connector" />
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Vertical layout
  return (
    <div className={clsx('stepper-indicator vertical', className, { compact })}>
      {steps.map((step, index) => (
        <div
          key={step.id}
          className={clsx('step-item', {
            clickable: index <= currentStep || !config.validateOnNext,
            current: index === currentStep,
            completed: step.status === 'completed',
            error: step.status === 'error',
          })}
          onClick={() => handleStepClick(index)}
        >
          <div className="step-marker">
            <motion.div
              className="step-circle"
              style={{ borderColor: getStepColor(step, index) }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <AnimatePresence mode="wait">
                {step.status === 'completed' ? (
                  <motion.div
                    key="check"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                    className="step-check"
                    style={{ color: config.colors?.completed }}
                  >
                    ✓
                  </motion.div>
                ) : step.status === 'error' ? (
                  <motion.div
                    key="error"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                    className="step-error"
                    style={{ color: config.colors?.error }}
                  >
                    ✕
                  </motion.div>
                ) : config.showNumbers ? (
                  <motion.span
                    key="number"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                    className="step-number"
                    style={{ color: getStepColor(step, index) }}
                  >
                    {index + 1}
                  </motion.span>
                ) : null}
              </AnimatePresence>
            </motion.div>

            {index < steps.length - 1 && (
              <div
                className="step-connector vertical"
                style={{
                  backgroundColor: index < currentStep
                    ? config.colors?.completed
                    : config.colors?.pending
                }}
              />
            )}
          </div>

          {showLabels && (
            <div className="step-content">
              <div className="step-title" style={{ color: getStepColor(step, index) }}>
                {step.title}
              </div>
              {step.description && !compact && (
                <div className="step-description">
                  {step.description}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Step content container
interface StepContentProps {
  children: React.ReactNode;
  className?: string;
  showNavigation?: boolean;
  navigationProps?: {
    nextLabel?: string;
    previousLabel?: string;
    completeLabel?: string;
    onNext?: () => Promise<boolean> | boolean;
    onPrevious?: () => void;
    customActions?: React.ReactNode;
  };
}

export function StepContent({
  children,
  className,
  showNavigation = true,
  navigationProps = {}
}: StepContentProps) {
  const {
    currentStep,
    totalSteps,
    canGoNext,
    canGoPrevious,
    isValidating,
    nextStep,
    previousStep,
    steps,
  } = useStepper();

  const {
    nextLabel = currentStep === totalSteps - 1 ? 'Complete' : 'Next',
    previousLabel = 'Previous',
    completeLabel = 'Complete',
    onNext,
    onPrevious,
    customActions,
  } = navigationProps;

  const handleNext = async () => {
    if (onNext) {
      const result = await onNext();
      if (result === false) return;
    }

    await nextStep();
  };

  const handlePrevious = () => {
    if (onPrevious) {
      onPrevious();
    } else {
      previousStep();
    }
  };

  const currentStepData = steps[currentStep];
  const isLastStep = currentStep === totalSteps - 1;

  return (
    <div className={clsx('stepper-content', className)}>
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2, ease: 'easeInOut' }}
          className="step-body"
        >
          {currentStepData?.error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="step-error-message"
            >
              {currentStepData.error}
            </motion.div>
          )}

          {children}
        </motion.div>
      </AnimatePresence>

      {showNavigation && (
        <div className="stepper-navigation">
          <div className="nav-left">
            {canGoPrevious && (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handlePrevious}
                className="nav-button previous"
                type="button"
              >
                {previousLabel}
              </motion.button>
            )}
          </div>

          <div className="nav-center">
            {customActions}
          </div>

          <div className="nav-right">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleNext}
              disabled={!canGoNext || isValidating}
              className={clsx('nav-button next', {
                loading: isValidating,
                complete: isLastStep,
              })}
              type="button"
            >
              {isValidating ? (
                <span className="loading-spinner" />
              ) : (
                isLastStep ? completeLabel : nextLabel
              )}
            </motion.button>
          </div>
        </div>
      )}
    </div>
  );
}

// Individual step wrapper component
interface StepProps {
  children: React.ReactNode;
  stepId: string;
  onValidate?: (data: unknown) => boolean | Promise<boolean>;
  onStepComplete?: (data: unknown) => void;
  className?: string;
}

export function Step({ children, stepId, onValidate, onStepComplete, className }: StepProps) {
  const { steps, currentStep, setStepData, setStepError } = useStepper();

  const stepIndex = steps.findIndex(step => step.id === stepId);
  const isCurrentStep = stepIndex === currentStep;
  const stepData = steps[stepIndex];

  // Validate step data when needed
  useEffect(() => {
    if (isCurrentStep && onValidate && stepData?.data) {
      const validateAsync = async () => {
        try {
          const isValid = await onValidate(stepData.data);
          if (!isValid) {
            setStepError(stepIndex, 'Validation failed');
          } else {
            setStepError(stepIndex, null);
          }
        } catch (error) {
          setStepError(stepIndex, error instanceof Error ? error.message : 'Validation error');
        }
      };

      validateAsync();
    }
  }, [isCurrentStep, stepData?.data, onValidate, stepIndex, setStepError]);

  // Handle step completion
  useEffect(() => {
    if (stepData?.status === 'completed' && onStepComplete && stepData.data) {
      onStepComplete(stepData.data);
    }
  }, [stepData?.status, stepData?.data, onStepComplete]);

  if (!isCurrentStep) {
    return null;
  }

  return (
    <div className={clsx('step-wrapper', className, `step-${stepId}`)}>
      {children}
    </div>
  );
}
