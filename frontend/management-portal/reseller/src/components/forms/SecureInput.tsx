/**
 * Secure input components with built-in validation and sanitization
 */

import React, { forwardRef, useState, useCallback } from 'react';
import { InputSanitizer } from '@/lib/security/input-sanitizer';
import { SecurityError } from '@/lib/security/types';

export interface SecureInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  label?: string;
  error?: string;
  validationType?: 'email' | 'url' | 'safeString' | 'number' | 'filename';
  onChange?: (value: string, isValid: boolean) => void;
  onValidationError?: (error: string) => void;
  sanitizeOnBlur?: boolean;
  validateOnChange?: boolean;
  min?: number;
  max?: number;
}

export const SecureInput = forwardRef<HTMLInputElement, SecureInputProps>(
  (
    {
      label,
      error,
      validationType = 'safeString',
      onChange,
      onValidationError,
      sanitizeOnBlur = true,
      validateOnChange = true,
      min,
      max,
      className = '',
      value,
      ...props
    },
    ref
  ) => {
    const [internalValue, setInternalValue] = useState(value || '');
    const [validationError, setValidationError] = useState<string>('');

    const validateInput = useCallback(
      (inputValue: string): { isValid: boolean; error?: string; sanitizedValue?: string } => {
        if (!inputValue) {
          return { isValid: true };
        }

        try {
          let sanitizedValue = inputValue;

          switch (validationType) {
            case 'email':
              sanitizedValue = InputSanitizer.sanitize_email(inputValue);
              break;
            case 'url':
              sanitizedValue = InputSanitizer.validate_url(inputValue, 'url');
              break;
            case 'filename':
              sanitizedValue = InputSanitizer.sanitize_filename(inputValue);
              break;
            case 'number':
              const numValue = InputSanitizer.validate_number(inputValue, 'number', min, max);
              sanitizedValue = numValue.toString();
              break;
            case 'safeString':
            default:
              sanitizedValue = InputSanitizer.validate_safe_input(inputValue, 'input');
              break;
          }

          return { isValid: true, sanitizedValue };
        } catch (error) {
          const errorMessage =
            error instanceof SecurityError
              ? error.reason
              : error instanceof Error
                ? error.message
                : 'Invalid input';

          return { isValid: false, error: errorMessage };
        }
      },
      [validationType, min, max]
    );

    const handleChange = useCallback(
      (event: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = event.target.value;
        setInternalValue(newValue);

        if (validateOnChange) {
          const validation = validateInput(newValue);
          setValidationError(validation.error || '');

          if (validation.error) {
            onValidationError?.(validation.error);
          }

          onChange?.(newValue, validation.isValid);
        } else {
          onChange?.(newValue, true);
        }
      },
      [validateOnChange, validateInput, onChange, onValidationError]
    );

    const handleBlur = useCallback(
      (event: React.FocusEvent<HTMLInputElement>) => {
        const currentValue = event.target.value;

        if (sanitizeOnBlur && currentValue) {
          const validation = validateInput(currentValue);

          if (
            validation.isValid &&
            validation.sanitizedValue &&
            validation.sanitizedValue !== currentValue
          ) {
            setInternalValue(validation.sanitizedValue);
            onChange?.(validation.sanitizedValue, true);
          }

          if (validation.error) {
            setValidationError(validation.error);
            onValidationError?.(validation.error);
          } else {
            setValidationError('');
          }
        }

        props.onBlur?.(event);
      },
      [sanitizeOnBlur, validateInput, onChange, onValidationError, props]
    );

    const inputClassName = `
      w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 
      ${error || validationError ? 'border-red-500 focus:ring-red-500' : 'border-gray-300'}
      ${className}
    `.trim();

    const displayError = error || validationError;

    return (
      <div className='space-y-1'>
        {label && (
          <label className='block text-sm font-medium text-gray-700'>
            {label}
            {props.required && <span className='text-red-500 ml-1'>*</span>}
          </label>
        )}

        <input
          ref={ref}
          {...props}
          value={internalValue}
          onChange={handleChange}
          onBlur={handleBlur}
          className={inputClassName}
          aria-invalid={!!displayError}
          aria-describedby={displayError ? `${props.id || 'input'}-error` : undefined}
        />

        {displayError && (
          <p id={`${props.id || 'input'}-error`} className='text-sm text-red-600' role='alert'>
            {displayError}
          </p>
        )}
      </div>
    );
  }
);

SecureInput.displayName = 'SecureInput';

export interface SecureTextareaProps
  extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'onChange'> {
  label?: string;
  error?: string;
  onChange?: (value: string, isValid: boolean) => void;
  onValidationError?: (error: string) => void;
  sanitizeOnBlur?: boolean;
  stripHtml?: boolean;
}

export const SecureTextarea = forwardRef<HTMLTextAreaElement, SecureTextareaProps>(
  (
    {
      label,
      error,
      onChange,
      onValidationError,
      sanitizeOnBlur = true,
      stripHtml = false,
      className = '',
      value,
      ...props
    },
    ref
  ) => {
    const [internalValue, setInternalValue] = useState(value || '');
    const [validationError, setValidationError] = useState<string>('');

    const validateAndSanitize = useCallback(
      (inputValue: string) => {
        if (!inputValue) return { isValid: true, sanitizedValue: inputValue };

        try {
          InputSanitizer.validate_safe_input(inputValue, 'textarea');

          const sanitizedValue = stripHtml
            ? InputSanitizer.strip_html(inputValue)
            : InputSanitizer.sanitize_html(inputValue);

          return { isValid: true, sanitizedValue };
        } catch (error) {
          const errorMessage =
            error instanceof SecurityError ? error.reason : 'Invalid content detected';

          return { isValid: false, error: errorMessage };
        }
      },
      [stripHtml]
    );

    const handleChange = useCallback(
      (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newValue = event.target.value;
        setInternalValue(newValue);

        const validation = validateAndSanitize(newValue);
        setValidationError(validation.error || '');

        if (validation.error) {
          onValidationError?.(validation.error);
        }

        onChange?.(newValue, validation.isValid);
      },
      [validateAndSanitize, onChange, onValidationError]
    );

    const handleBlur = useCallback(
      (event: React.FocusEvent<HTMLTextAreaElement>) => {
        const currentValue = event.target.value;

        if (sanitizeOnBlur && currentValue) {
          const validation = validateAndSanitize(currentValue);

          if (
            validation.isValid &&
            validation.sanitizedValue &&
            validation.sanitizedValue !== currentValue
          ) {
            setInternalValue(validation.sanitizedValue);
            onChange?.(validation.sanitizedValue, true);
          }
        }

        props.onBlur?.(event);
      },
      [sanitizeOnBlur, validateAndSanitize, onChange, props]
    );

    const textareaClassName = `
      w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical
      ${error || validationError ? 'border-red-500 focus:ring-red-500' : 'border-gray-300'}
      ${className}
    `.trim();

    const displayError = error || validationError;

    return (
      <div className='space-y-1'>
        {label && (
          <label className='block text-sm font-medium text-gray-700'>
            {label}
            {props.required && <span className='text-red-500 ml-1'>*</span>}
          </label>
        )}

        <textarea
          ref={ref}
          {...props}
          value={internalValue}
          onChange={handleChange}
          onBlur={handleBlur}
          className={textareaClassName}
          aria-invalid={!!displayError}
          aria-describedby={displayError ? `${props.id || 'textarea'}-error` : undefined}
        />

        {displayError && (
          <p id={`${props.id || 'textarea'}-error`} className='text-sm text-red-600' role='alert'>
            {displayError}
          </p>
        )}
      </div>
    );
  }
);

SecureTextarea.displayName = 'SecureTextarea';

export interface SecureSelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  label?: string;
  error?: string;
  options: Array<{ value: string; label: string; disabled?: boolean }>;
  placeholder?: string;
  onChange?: (value: string, isValid: boolean) => void;
  onValidationError?: (error: string) => void;
}

export const SecureSelect = forwardRef<HTMLSelectElement, SecureSelectProps>(
  (
    {
      label,
      error,
      options,
      placeholder,
      onChange,
      onValidationError,
      className = '',
      value,
      ...props
    },
    ref
  ) => {
    const [validationError, setValidationError] = useState<string>('');

    const handleChange = useCallback(
      (event: React.ChangeEvent<HTMLSelectElement>) => {
        const newValue = event.target.value;

        try {
          // Validate that the selected value is in the allowed options
          const isValidOption = options.some((option) => option.value === newValue);

          if (newValue && !isValidOption) {
            throw new SecurityError('select', 'Invalid option selected');
          }

          // Sanitize the value
          const sanitizedValue = InputSanitizer.validate_safe_input(newValue, 'select');
          setValidationError('');
          onChange?.(sanitizedValue, true);
        } catch (error) {
          const errorMessage = error instanceof SecurityError ? error.reason : 'Invalid selection';

          setValidationError(errorMessage);
          onValidationError?.(errorMessage);
          onChange?.(newValue, false);
        }
      },
      [options, onChange, onValidationError]
    );

    const selectClassName = `
      w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500
      ${error || validationError ? 'border-red-500 focus:ring-red-500' : 'border-gray-300'}
      ${className}
    `.trim();

    const displayError = error || validationError;

    return (
      <div className='space-y-1'>
        {label && (
          <label className='block text-sm font-medium text-gray-700'>
            {label}
            {props.required && <span className='text-red-500 ml-1'>*</span>}
          </label>
        )}

        <select
          ref={ref}
          {...props}
          value={value || ''}
          onChange={handleChange}
          className={selectClassName}
          aria-invalid={!!displayError}
          aria-describedby={displayError ? `${props.id || 'select'}-error` : undefined}
        >
          {placeholder && (
            <option value='' disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>

        {displayError && (
          <p id={`${props.id || 'select'}-error`} className='text-sm text-red-600' role='alert'>
            {displayError}
          </p>
        )}
      </div>
    );
  }
);

SecureSelect.displayName = 'SecureSelect';
