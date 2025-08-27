/**
 * React Hook for Input Sanitization
 * 
 * Provides reactive input sanitization for forms and user inputs
 * with real-time validation and feedback.
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { InputSanitizer, SanitizationConfig, SanitizationResult } from '../sanitization/input-sanitizer';

export interface UseSanitizedInputOptions extends SanitizationConfig {
  type?: 'text' | 'email' | 'phone' | 'number' | 'path';
  validateOnChange?: boolean;
  debounceMs?: number;
  onViolation?: (violations: string[]) => void;
  onSanitize?: (original: string, sanitized: string) => void;
}

export interface UseSanitizedInputReturn {
  value: string;
  sanitizedValue: string;
  isValid: boolean;
  violations: string[];
  wasModified: boolean;
  setValue: (value: string) => void;
  sanitize: () => SanitizationResult;
  reset: () => void;
  inputProps: {
    value: string;
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
    onBlur: () => void;
  };
}

export function useSanitizedInput(
  initialValue: string = '',
  options: UseSanitizedInputOptions = {}
): UseSanitizedInputReturn {
  const [value, setValue] = useState<string>(initialValue);
  const [sanitizedValue, setSanitizedValue] = useState<string>(initialValue);
  const [result, setResult] = useState<SanitizationResult>({
    sanitized: initialValue,
    wasModified: false,
    violations: [],
    isValid: true,
  });

  const sanitizer = useMemo(() => new InputSanitizer(options), [
    options.allowedTags,
    options.allowedAttributes,
    options.maxLength,
    options.stripWhitespace,
    options.preserveNewlines,
    options.allowEmptyValues,
  ]);

  const performSanitization = useCallback((inputValue: string): SanitizationResult => {
    let sanitizationResult: SanitizationResult;

    switch (options.type) {
      case 'email':
        sanitizationResult = sanitizer.sanitizeEmail(inputValue);
        break;
      case 'phone':
        sanitizationResult = sanitizer.sanitizePhone(inputValue);
        break;
      case 'number':
        sanitizationResult = sanitizer.sanitizeNumber(inputValue, options);
        break;
      case 'path':
        sanitizationResult = sanitizer.sanitizePath(inputValue);
        break;
      default:
        sanitizationResult = sanitizer.sanitizeText(inputValue, options);
    }

    return sanitizationResult;
  }, [sanitizer, options.type]);

  const sanitize = useCallback((): SanitizationResult => {
    const sanitizationResult = performSanitization(value);
    
    setSanitizedValue(sanitizationResult.sanitized);
    setResult(sanitizationResult);

    // Call callbacks
    if (sanitizationResult.violations.length > 0 && options.onViolation) {
      options.onViolation(sanitizationResult.violations);
    }

    if (sanitizationResult.wasModified && options.onSanitize) {
      options.onSanitize(value, sanitizationResult.sanitized);
    }

    return sanitizationResult;
  }, [value, performSanitization, options.onViolation, options.onSanitize]);

  const handleSetValue = useCallback((newValue: string) => {
    setValue(newValue);

    if (options.validateOnChange) {
      const sanitizationResult = performSanitization(newValue);
      setSanitizedValue(sanitizationResult.sanitized);
      setResult(sanitizationResult);

      if (sanitizationResult.violations.length > 0 && options.onViolation) {
        options.onViolation(sanitizationResult.violations);
      }
    }
  }, [performSanitization, options.validateOnChange, options.onViolation]);

  const handleInputChange = useCallback((event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const newValue = event.target.value;
    handleSetValue(newValue);
  }, [handleSetValue]);

  const handleBlur = useCallback(() => {
    const sanitizationResult = sanitize();
    
    // Auto-correct the input value with sanitized value on blur
    if (sanitizationResult.wasModified && sanitizationResult.isValid) {
      setValue(sanitizationResult.sanitized);
    }
  }, [sanitize]);

  const reset = useCallback(() => {
    setValue(initialValue);
    setSanitizedValue(initialValue);
    setResult({
      sanitized: initialValue,
      wasModified: false,
      violations: [],
      isValid: true,
    });
  }, [initialValue]);

  // Debounced sanitization
  useEffect(() => {
    if (!options.validateOnChange || !options.debounceMs) {
      return;
    }

    const timeoutId = setTimeout(() => {
      const sanitizationResult = performSanitization(value);
      setSanitizedValue(sanitizationResult.sanitized);
      setResult(sanitizationResult);
    }, options.debounceMs);

    return () => clearTimeout(timeoutId);
  }, [value, performSanitization, options.validateOnChange, options.debounceMs]);

  const inputProps = useMemo(() => ({
    value,
    onChange: handleInputChange,
    onBlur: handleBlur,
  }), [value, handleInputChange, handleBlur]);

  return {
    value,
    sanitizedValue,
    isValid: result.isValid,
    violations: result.violations,
    wasModified: result.wasModified,
    setValue: handleSetValue,
    sanitize,
    reset,
    inputProps,
  };
}

/**
 * Hook for sanitizing form objects
 */
export interface UseSanitizedFormOptions<T> {
  fieldConfigs: Record<keyof T, SanitizationConfig & { type?: 'text' | 'email' | 'phone' | 'number' | 'path' }>;
  validateOnChange?: boolean;
  onViolation?: (field: keyof T, violations: string[]) => void;
}

export interface UseSanitizedFormReturn<T> {
  values: T;
  sanitizedValues: T;
  violations: Record<keyof T, string[]>;
  isValid: boolean;
  setField: (field: keyof T, value: any) => void;
  setValues: (values: Partial<T>) => void;
  sanitizeAll: () => void;
  reset: () => void;
}

export function useSanitizedForm<T extends Record<string, any>>(
  initialValues: T,
  options: UseSanitizedFormOptions<T>
): UseSanitizedFormReturn<T> {
  const [values, setValues] = useState<T>(initialValues);
  const [sanitizedValues, setSanitizedValues] = useState<T>(initialValues);
  const [violations, setViolations] = useState<Record<keyof T, string[]>>({} as Record<keyof T, string[]>);

  const sanitizer = useMemo(() => new InputSanitizer(), []);

  const sanitizeField = useCallback((field: keyof T, value: any) => {
    const config = options.fieldConfigs[field];
    if (!config) return { sanitized: value, violations: [], isValid: true };

    let result: SanitizationResult;
    switch (config.type) {
      case 'email':
        result = sanitizer.sanitizeEmail(value);
        break;
      case 'phone':
        result = sanitizer.sanitizePhone(value);
        break;
      case 'number':
        result = sanitizer.sanitizeNumber(value, config);
        break;
      case 'path':
        result = sanitizer.sanitizePath(value);
        break;
      default:
        result = sanitizer.sanitizeText(value, config);
    }

    if (result.violations.length > 0 && options.onViolation) {
      options.onViolation(field, result.violations);
    }

    return result;
  }, [sanitizer, options.fieldConfigs, options.onViolation]);

  const setField = useCallback((field: keyof T, value: any) => {
    setValues(prev => ({ ...prev, [field]: value }));

    if (options.validateOnChange) {
      const result = sanitizeField(field, value);
      setSanitizedValues(prev => ({ ...prev, [field]: result.sanitized }));
      setViolations(prev => ({ ...prev, [field]: result.violations }));
    }
  }, [sanitizeField, options.validateOnChange]);

  const setFormValues = useCallback((newValues: Partial<T>) => {
    setValues(prev => ({ ...prev, ...newValues }));

    if (options.validateOnChange) {
      const newSanitizedValues = { ...sanitizedValues };
      const newViolations = { ...violations };

      for (const [key, value] of Object.entries(newValues)) {
        const result = sanitizeField(key as keyof T, value);
        newSanitizedValues[key as keyof T] = result.sanitized;
        newViolations[key as keyof T] = result.violations;
      }

      setSanitizedValues(newSanitizedValues);
      setViolations(newViolations);
    }
  }, [sanitizeField, sanitizedValues, violations, options.validateOnChange]);

  const sanitizeAll = useCallback(() => {
    const { sanitized, violations: allViolations } = sanitizer.sanitizeObject(values, options.fieldConfigs);
    setSanitizedValues(sanitized);
    setViolations(allViolations);
  }, [sanitizer, values, options.fieldConfigs]);

  const reset = useCallback(() => {
    setValues(initialValues);
    setSanitizedValues(initialValues);
    setViolations({} as Record<keyof T, string[]>);
  }, [initialValues]);

  const isValid = useMemo(() => {
    return Object.values(violations).every(fieldViolations => 
      fieldViolations.length === 0 || fieldViolations.every(v => 
        v.includes('Applied') || v.includes('sanitized')
      )
    );
  }, [violations]);

  return {
    values,
    sanitizedValues,
    violations,
    isValid,
    setField,
    setValues: setFormValues,
    sanitizeAll,
    reset,
  };
}