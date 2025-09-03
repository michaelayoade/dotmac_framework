/**
 * Secure Component HOC and Security Hooks
 *
 * Provides component-level security validation and protection
 */

import React, { useCallback, useMemo } from 'react';
import { InputValidator, type ValidationResult } from '../validation/InputValidation';

// Security context for component-level security settings
interface SecurityContextValue {
  enableValidation: boolean;
  enableSanitization: boolean;
  logSecurityEvents: boolean;
  validator: InputValidator;
}

const SecurityContext = React.createContext<SecurityContextValue | null>(null);

export interface SecurityProviderProps {
  children: React.ReactNode;
  enableValidation?: boolean;
  enableSanitization?: boolean;
  logSecurityEvents?: boolean;
  validator?: InputValidator;
}

/**
 * Security Provider Component
 */
export function SecurityProvider({
  children,
  enableValidation = true,
  enableSanitization = true,
  logSecurityEvents = process.env.NODE_ENV === 'development',
  validator = InputValidator.forTextInput(),
}: SecurityProviderProps) {
  const contextValue = useMemo(
    () => ({
      enableValidation,
      enableSanitization,
      logSecurityEvents,
      validator,
    }),
    [enableValidation, enableSanitization, logSecurityEvents, validator]
  );

  return <SecurityContext.Provider value={contextValue}>{children}</SecurityContext.Provider>;
}

/**
 * Hook to use security context
 */
export function useSecurity() {
  const context = React.useContext(SecurityContext);
  if (!context) {
    throw new Error('useSecurity must be used within a SecurityProvider');
  }
  return context;
}

/**
 * Hook for input validation
 */
export function useInputValidation(customValidator?: InputValidator) {
  const { validator: defaultValidator, enableValidation, logSecurityEvents } = useSecurity();
  const validator = customValidator || defaultValidator;

  const validateInput = useCallback(
    (input: string): ValidationResult => {
      if (!enableValidation) {
        return {
          isValid: true,
          sanitizedValue: input,
          errors: [],
          warnings: [],
          metadata: {
            originalLength: input.length,
            sanitizedLength: input.length,
            rulesApplied: [],
            processingTime: 0,
            hash: '',
          },
        };
      }

      const result = validator.validate(input);

      if (logSecurityEvents && (result.errors.length > 0 || result.warnings.length > 0)) {
        console.warn('Security validation result:', {
          input: input.substring(0, 100) + (input.length > 100 ? '...' : ''),
          errors: result.errors,
          warnings: result.warnings,
        });
      }

      return result;
    },
    [validator, enableValidation, logSecurityEvents]
  );

  return { validateInput };
}

/**
 * Hook for secure form handling
 */
export function useSecureForm(validationSchema?: Record<string, InputValidator>) {
  const { validateInput } = useInputValidation();
  const [validationResults, setValidationResults] = React.useState<
    Record<string, ValidationResult>
  >({});
  const [isValid, setIsValid] = React.useState(true);

  const validateField = useCallback(
    (name: string, value: string, customValidator?: InputValidator) => {
      const validator = customValidator || validationSchema?.[name];
      const result = validator ? validator.validate(value) : validateInput(value);

      setValidationResults((prev) => ({
        ...prev,
        [name]: result,
      }));

      // Update overall form validity
      const allResults = { ...validationResults, [name]: result };
      const formIsValid = Object.values(allResults).every((r) => r.isValid);
      setIsValid(formIsValid);

      return result;
    },
    [validateInput, validationSchema, validationResults]
  );

  const validateForm = useCallback(
    (formData: Record<string, string>) => {
      const results: Record<string, ValidationResult> = {};
      let formIsValid = true;

      for (const [name, value] of Object.entries(formData)) {
        const validator = validationSchema?.[name];
        const result = validator ? validator.validate(value) : validateInput(value);

        results[name] = result;
        if (!result.isValid) {
          formIsValid = false;
        }
      }

      setValidationResults(results);
      setIsValid(formIsValid);

      return { results, isValid: formIsValid };
    },
    [validateInput, validationSchema]
  );

  const getSanitizedFormData = useCallback(
    (formData: Record<string, string>) => {
      const sanitized: Record<string, string> = {};

      for (const [name, value] of Object.entries(formData)) {
        const result = validationResults[name] || validateField(name, value);
        sanitized[name] = result.sanitizedValue;
      }

      return sanitized;
    },
    [validationResults, validateField]
  );

  return {
    validationResults,
    isValid,
    validateField,
    validateForm,
    getSanitizedFormData,
  };
}

/**
 * HOC for securing components
 */
export interface SecureComponentOptions {
  validator?: InputValidator;
  enableValidation?: boolean;
  enableSanitization?: boolean;
  logSecurityEvents?: boolean;
}

export function withSecurity<P extends object>(
  Component: React.ComponentType<P>,
  options: SecureComponentOptions = {}
) {
  const SecureComponent = React.forwardRef<any, P & SecureComponentOptions>((props, ref) => {
    const mergedOptions = { ...options, ...props };
    const {
      enableValidation,
      enableSanitization,
      logSecurityEvents,
      validator,
      ...componentProps
    } = props as any;

    return (
      <SecurityProvider {...mergedOptions}>
        <Component {...componentProps} ref={ref} />
      </SecurityProvider>
    );
  });

  SecureComponent.displayName = `withSecurity(${Component.displayName || Component.name})`;

  return SecureComponent;
}

/**
 * Hook for component security monitoring
 */
export function useSecurityMonitoring(componentId: string) {
  const { logSecurityEvents } = useSecurity();
  const [securityEvents, setSecurityEvents] = React.useState<
    Array<{
      timestamp: Date;
      event: string;
      details: any;
    }>
  >([]);

  const logSecurityEvent = useCallback(
    (event: string, details: any) => {
      const securityEvent = {
        timestamp: new Date(),
        event,
        details: {
          componentId,
          ...details,
        },
      };

      if (logSecurityEvents) {
        console.warn(`[Security Event - ${componentId}]`, securityEvent);
      }

      setSecurityEvents((prev) => [...prev.slice(-99), securityEvent]);
    },
    [componentId, logSecurityEvents]
  );

  const reportSuspiciousActivity = useCallback(
    (activity: string, metadata?: any) => {
      logSecurityEvent('suspicious_activity', {
        activity,
        metadata,
        userAgent: typeof window !== 'undefined' ? window.navigator.userAgent : 'unknown',
        timestamp: new Date().toISOString(),
      });
    },
    [logSecurityEvent]
  );

  const reportValidationFailure = useCallback(
    (input: string, errors: any[]) => {
      logSecurityEvent('validation_failure', {
        inputPreview: input.substring(0, 100),
        inputLength: input.length,
        errors: errors.map((e) => ({ rule: e.rule, message: e.message })),
      });
    },
    [logSecurityEvent]
  );

  return {
    securityEvents,
    logSecurityEvent,
    reportSuspiciousActivity,
    reportValidationFailure,
  };
}
