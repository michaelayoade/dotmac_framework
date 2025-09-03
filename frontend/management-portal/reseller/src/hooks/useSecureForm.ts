/**
 * Secure form handling hook with input sanitization
 * Integrates with React Hook Form and provides automatic validation
 */

import { useForm, UseFormProps, FieldValues, Path } from 'react-hook-form';
import { useCallback, useMemo } from 'react';
import { InputSanitizer, FormValidators } from '@/lib/security/input-sanitizer';
import { SecurityError } from '@/lib/security/types';

export interface SecureFormOptions<T extends FieldValues> extends UseFormProps<T> {
  sanitizeOnSubmit?: boolean;
  validateOnChange?: boolean;
  securityRules?: Partial<Record<Path<T>, ValidationRule>>;
}

export interface ValidationRule {
  type: 'email' | 'url' | 'safeString' | 'number' | 'filename' | 'custom';
  customValidator?: (value: any) => string | true;
  min?: number;
  max?: number;
  required?: boolean;
}

export function useSecureForm<T extends FieldValues>(options: SecureFormOptions<T> = {}) {
  const {
    sanitizeOnSubmit = true,
    validateOnChange = true,
    securityRules = {},
    ...formOptions
  } = options;

  const form = useForm<T>({
    ...formOptions,
    mode: validateOnChange ? 'onChange' : formOptions.mode,
  });

  // Create validation rules based on security rules
  const validationRules = useMemo(() => {
    const rules: Record<string, any> = {};

    Object.entries(securityRules).forEach(([fieldName, rule]: [string, any]) => {
      rules[fieldName] = {
        required: rule.required ? `${fieldName} is required` : false,
        validate: (value: any) => {
          if (!value && !rule.required) return true;

          try {
            switch (rule.type) {
              case 'email':
                return FormValidators.email(value) || true;
              case 'url':
                return FormValidators.url(fieldName)(value) || true;
              case 'safeString':
                return FormValidators.safeString(fieldName)(value) || true;
              case 'number':
                return FormValidators.number(fieldName, rule.min, rule.max)(value) || true;
              case 'filename':
                return FormValidators.filename(value) || true;
              case 'custom':
                return rule.customValidator ? rule.customValidator(value) : true;
              default:
                return FormValidators.safeString(fieldName)(value) || true;
            }
          } catch (error) {
            if (error instanceof SecurityError) {
              return error.reason;
            }
            return 'Invalid input';
          }
        },
      };
    });

    return rules;
  }, [securityRules]);

  // Enhanced submit handler with sanitization
  const handleSubmitSecure = useCallback(
    (onSubmit: (data: T) => void | Promise<void>) => {
      return form.handleSubmit(async (data: T) => {
        try {
          let sanitizedData = data;

          if (sanitizeOnSubmit) {
            // Sanitize form data before submission
            sanitizedData = sanitizeFormData(data, securityRules);
          }

          await onSubmit(sanitizedData);
        } catch (error) {
          console.error('Secure form submission error:', error);

          if (error instanceof SecurityError) {
            form.setError(error.field as Path<T>, {
              type: 'security',
              message: error.reason,
            });
          } else {
            // Set general form error
            form.setError('root', {
              type: 'submission',
              message: error instanceof Error ? error.message : 'Form submission failed',
            });
          }
        }
      });
    },
    [form, sanitizeOnSubmit, securityRules]
  );

  // Secure field registration with automatic validation
  const registerSecure = useCallback(
    (name: Path<T>, options: any = {}) => {
      const fieldRules = validationRules[name] || {};

      return form.register(name, {
        ...options,
        ...fieldRules,
      });
    },
    [form, validationRules]
  );

  // Validate individual field
  const validateField = useCallback(
    (name: Path<T>, value: any) => {
      const rule = (securityRules as any)[name];
      if (!rule) return true;

      try {
        switch (rule.type) {
          case 'email':
            InputSanitizer.sanitize_email(value);
            break;
          case 'url':
            InputSanitizer.validate_url(value, name);
            break;
          case 'safeString':
            InputSanitizer.validate_safe_input(value, name);
            break;
          case 'number':
            InputSanitizer.validate_number(value, name, rule.min, rule.max);
            break;
          case 'filename':
            InputSanitizer.sanitize_filename(value);
            break;
          case 'custom':
            if (rule.customValidator) {
              const result = rule.customValidator(value);
              if (result !== true) throw new Error(result);
            }
            break;
        }
        return true;
      } catch (error) {
        if (error instanceof SecurityError) {
          return error.reason;
        }
        return error instanceof Error ? error.message : 'Invalid input';
      }
    },
    [securityRules]
  );

  return {
    ...form,
    handleSubmitSecure,
    registerSecure,
    validateField,
    validationRules,
  };
}

/**
 * Sanitize form data recursively
 */
function sanitizeFormData<T extends FieldValues>(
  data: T,
  securityRules: Partial<Record<Path<T>, ValidationRule>>
): T {
  const sanitized = { ...data };

  Object.entries(sanitized).forEach(([key, value]) => {
    const rule = securityRules[key as Path<T>];

    if (typeof value === 'string' && value) {
      try {
        switch (rule?.type) {
          case 'email':
            sanitized[key as keyof T] = InputSanitizer.sanitize_email(value) as T[keyof T];
            break;
          case 'filename':
            sanitized[key as keyof T] = InputSanitizer.sanitize_filename(value) as T[keyof T];
            break;
          case 'url':
            sanitized[key as keyof T] = InputSanitizer.validate_url(value, key) as T[keyof T];
            break;
          default:
            sanitized[key as keyof T] = InputSanitizer.sanitize_html(value) as T[keyof T];
            break;
        }
      } catch (error) {
        console.warn(`Failed to sanitize field ${key}:`, error);
        // Keep original value if sanitization fails
      }
    } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      sanitized[key as keyof T] = InputSanitizer.sanitize_json_input(value) as T[keyof T];
    }
  });

  return sanitized;
}

/**
 * Common security rules for forms
 */
export const CommonSecurityRules = {
  email: { type: 'email' as const, required: true },
  password: { type: 'safeString' as const, required: true },
  name: { type: 'safeString' as const, required: true },
  company: { type: 'safeString' as const, required: true },
  phone: { type: 'safeString' as const },
  website: { type: 'url' as const },
  notes: { type: 'safeString' as const },
  filename: { type: 'filename' as const },
  amount: { type: 'number' as const, min: 0 },
};
