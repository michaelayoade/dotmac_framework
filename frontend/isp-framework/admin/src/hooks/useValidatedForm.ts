/**
 * Validated Form Hook
 * Provides form state management with real-time validation using Zod schemas
 */

import { useState, useCallback, useMemo } from 'react';
import { z } from 'zod';
import { validateSchema } from '../lib/schemas';

interface ValidationErrors {
  [key: string]: string[];
}

interface UseValidatedFormOptions<T> {
  initialData: T;
  schema: z.ZodSchema<T>;
  onSubmit?: (data: T) => Promise<void> | void;
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
}

interface UseValidatedFormReturn<T> {
  data: T;
  errors: ValidationErrors;
  isValid: boolean;
  isSubmitting: boolean;
  isDirty: boolean;
  touched: Record<string, boolean>;

  // Form handlers
  handleChange: (field: keyof T, value: any) => void;
  handleBlur: (field: keyof T) => void;
  handleSubmit: (e?: React.FormEvent) => Promise<void>;
  handleReset: () => void;

  // Validation methods
  validateField: (field: keyof T) => string[] | null;
  validateForm: () => boolean;
  clearErrors: () => void;
  setFieldError: (field: keyof T, errors: string[]) => void;

  // Utilities
  getFieldProps: (field: keyof T) => {
    name: string;
    value: any;
    onChange: (
      e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
    ) => void;
    onBlur: (
      e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
    ) => void;
    'aria-invalid': boolean;
    'aria-describedby': string;
  };
}

export function useValidatedForm<T extends Record<string, any>>({
  initialData,
  schema,
  onSubmit,
  validateOnChange = true,
  validateOnBlur = true,
}: UseValidatedFormOptions<T>): UseValidatedFormReturn<T> {
  const [data, setData] = useState<T>(initialData);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  // Check if form is dirty (has changes from initial data)
  const isDirty = useMemo(() => {
    return JSON.stringify(data) !== JSON.stringify(initialData);
  }, [data, initialData]);

  // Check if form is valid
  const isValid = useMemo(() => {
    const result = validateSchema(schema, data);
    return result.success;
  }, [data, schema]);

  // Validate a specific field
  const validateField = useCallback(
    (field: keyof T): string[] | null => {
      try {
        const fieldSchema = schema.shape?.[field as string];
        if (!fieldSchema) return null;

        fieldSchema.parse(data[field]);
        return null;
      } catch (error) {
        if (error instanceof z.ZodError) {
          return error.errors.map((err) => err.message);
        }
        return ['Validation error'];
      }
    },
    [data, schema]
  );

  // Validate entire form
  const validateForm = useCallback((): boolean => {
    const result = validateSchema(schema, data);

    if (!result.success) {
      const newErrors: ValidationErrors = {};

      // Parse Zod errors and group by field
      result.errors.forEach((error) => {
        const [fieldPath, message] = error.split(': ');
        const field = fieldPath || 'form';

        if (!newErrors[field]) {
          newErrors[field] = [];
        }
        newErrors[field].push(message || 'Validation error');
      });

      setErrors(newErrors);
      return false;
    }

    setErrors({});
    return true;
  }, [data, schema]);

  // Handle field changes
  const handleChange = useCallback(
    (field: keyof T, value: any) => {
      setData((prev) => ({ ...prev, [field]: value }));

      // Real-time validation if enabled
      if (validateOnChange && touched[field as string]) {
        const fieldErrors = validateField(field);
        setErrors((prev) => ({
          ...prev,
          [field]: fieldErrors || [],
        }));
      }
    },
    [validateOnChange, touched, validateField]
  );

  // Handle field blur
  const handleBlur = useCallback(
    (field: keyof T) => {
      setTouched((prev) => ({ ...prev, [field as string]: true }));

      // Validation on blur if enabled
      if (validateOnBlur) {
        const fieldErrors = validateField(field);
        setErrors((prev) => ({
          ...prev,
          [field]: fieldErrors || [],
        }));
      }
    },
    [validateOnBlur, validateField]
  );

  // Handle form submission
  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      if (e) {
        e.preventDefault();
      }

      // Mark all fields as touched
      const allTouched = Object.keys(data).reduce(
        (acc, key) => ({
          ...acc,
          [key]: true,
        }),
        {}
      );
      setTouched(allTouched);

      // Validate form
      if (!validateForm()) {
        return;
      }

      // Submit if valid
      if (onSubmit) {
        setIsSubmitting(true);
        try {
          await onSubmit(data);
        } catch (error) {
          console.error('Form submission error:', error);
          // You might want to set form-level errors here
        } finally {
          setIsSubmitting(false);
        }
      }
    },
    [data, validateForm, onSubmit]
  );

  // Reset form to initial state
  const handleReset = useCallback(() => {
    setData(initialData);
    setErrors({});
    setTouched({});
  }, [initialData]);

  // Clear all errors
  const clearErrors = useCallback(() => {
    setErrors({});
  }, []);

  // Set error for specific field
  const setFieldError = useCallback((field: keyof T, fieldErrors: string[]) => {
    setErrors((prev) => ({
      ...prev,
      [field]: fieldErrors,
    }));
  }, []);

  // Get props for input fields
  const getFieldProps = useCallback(
    (field: keyof T) => {
      const fieldName = field as string;

      return {
        name: fieldName,
        value: data[field] || '',
        onChange: (
          e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
        ) => {
          handleChange(field, e.target.value);
        },
        onBlur: (
          e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
        ) => {
          handleBlur(field);
        },
        'aria-invalid': !!(errors[fieldName] && errors[fieldName].length > 0),
        'aria-describedby': `${fieldName}-error`,
      };
    },
    [data, errors, handleChange, handleBlur]
  );

  return {
    data,
    errors,
    isValid,
    isSubmitting,
    isDirty,
    touched,

    handleChange,
    handleBlur,
    handleSubmit,
    handleReset,

    validateField,
    validateForm,
    clearErrors,
    setFieldError,

    getFieldProps,
  };
}

// Hook for field-level validation errors display
export function useFieldErrors(fieldName: string, errors: ValidationErrors) {
  const fieldErrors = errors[fieldName] || [];
  const hasErrors = fieldErrors.length > 0;

  return {
    hasErrors,
    errors: fieldErrors,
    errorMessage: fieldErrors.join(', '),
  };
}
