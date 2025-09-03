/**
 * Accessible Form Components
 * Provides comprehensive form validation and accessibility features
 */

import { AlertCircle, Check, Eye, EyeOff } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import type { FormErrors, FormField } from '../../types';

// Enhanced Input with validation and accessibility
export function AccessibleInput({
  field,
  value,
  onChange,
  error,
  disabled = false,
  className = '',
  autoComplete,
  ...props
}: {
  field: FormField;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  className?: string;
  autoComplete?: string;
  [key: string]: any;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const id = `field-${field.name}`;
  const errorId = `${id}-error`;
  const helpId = `${id}-help`;

  const isPassword = field.type === 'password';
  const inputType = isPassword && showPassword ? 'text' : field.type;

  // Focus management for accessibility
  const handleFocus = () => setIsFocused(true);
  const handleBlur = () => setIsFocused(false);

  // Validation styling
  const getValidationClasses = () => {
    if (error) return 'border-red-500 focus:border-red-500 focus:ring-red-200';
    if (value && !error) return 'border-green-500 focus:border-green-500 focus:ring-green-200';
    return 'border-gray-300 focus:border-blue-500 focus:ring-blue-200';
  };

  return (
    <div className='space-y-2'>
      <label
        htmlFor={id}
        className={`block text-sm font-medium transition-colors ${
          error ? 'text-red-700' : 'text-gray-700'
        } ${field.required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}`}
      >
        {field.label}
      </label>

      <div className='relative'>
        <input
          ref={inputRef}
          id={id}
          name={field.name}
          type={inputType}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={field.placeholder}
          disabled={disabled}
          required={field.required}
          autoComplete={autoComplete}
          className={`
            block w-full px-3 py-2 text-sm rounded-md transition-all duration-200
            ${getValidationClasses()}
            ${disabled ? 'bg-gray-50 cursor-not-allowed' : 'bg-white'}
            ${isPassword ? 'pr-12' : 'pr-3'}
            focus:outline-none focus:ring-2
            ${className}
          `}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={`${error ? errorId : ''} ${field.placeholder ? helpId : ''}`}
          minLength={field.validation?.minLength}
          maxLength={field.validation?.maxLength}
          pattern={field.validation?.pattern?.source}
          {...props}
        />

        {/* Password visibility toggle */}
        {isPassword && (
          <button
            type='button'
            onClick={() => setShowPassword(!showPassword)}
            className='absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600'
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            tabIndex={-1}
          >
            {showPassword ? <EyeOff className='h-4 w-4' /> : <Eye className='h-4 w-4' />}
          </button>
        )}

        {/* Validation indicator */}
        {value && !isPassword && (
          <div className='absolute inset-y-0 right-0 flex items-center pr-3'>
            {error ? (
              <AlertCircle className='h-4 w-4 text-red-500' />
            ) : (
              <Check className='h-4 w-4 text-green-500' />
            )}
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div id={errorId} className='flex items-center text-sm text-red-600' role='alert'>
          <AlertCircle className='h-4 w-4 mr-1 flex-shrink-0' />
          <span>{error}</span>
        </div>
      )}

      {/* Help text */}
      {field.placeholder && !error && (
        <div id={helpId} className='text-xs text-gray-500'>
          {field.placeholder}
        </div>
      )}
    </div>
  );
}

// Enhanced Select with accessibility
export function AccessibleSelect({
  field,
  value,
  onChange,
  error,
  disabled = false,
  className = '',
  ...props
}: {
  field: FormField & { options: Array<{ value: string; label: string }> };
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  className?: string;
  [key: string]: any;
}) {
  const id = `field-${field.name}`;
  const errorId = `${id}-error`;

  const getValidationClasses = () => {
    if (error) return 'border-red-500 focus:border-red-500 focus:ring-red-200';
    if (value && !error) return 'border-green-500 focus:border-green-500 focus:ring-green-200';
    return 'border-gray-300 focus:border-blue-500 focus:ring-blue-200';
  };

  return (
    <div className='space-y-2'>
      <label
        htmlFor={id}
        className={`block text-sm font-medium ${
          error ? 'text-red-700' : 'text-gray-700'
        } ${field.required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}`}
      >
        {field.label}
      </label>

      <select
        id={id}
        name={field.name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        required={field.required}
        className={`
          block w-full px-3 py-2 text-sm rounded-md transition-all duration-200
          ${getValidationClasses()}
          ${disabled ? 'bg-gray-50 cursor-not-allowed' : 'bg-white'}
          focus:outline-none focus:ring-2
          ${className}
        `}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? errorId : undefined}
        {...props}
      >
        <option value='' disabled>
          {field.placeholder || `Select ${field.label.toLowerCase()}`}
        </option>
        {field.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      {error && (
        <div id={errorId} className='flex items-center text-sm text-red-600' role='alert'>
          <AlertCircle className='h-4 w-4 mr-1 flex-shrink-0' />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

// Enhanced Textarea with accessibility
export function AccessibleTextarea({
  field,
  value,
  onChange,
  error,
  disabled = false,
  rows = 4,
  className = '',
  ...props
}: {
  field: FormField;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  rows?: number;
  className?: string;
  [key: string]: any;
}) {
  const id = `field-${field.name}`;
  const errorId = `${id}-error`;
  const counterId = `${id}-counter`;

  const maxLength = field.validation?.maxLength;
  const remainingChars = maxLength ? maxLength - value.length : null;

  const getValidationClasses = () => {
    if (error) return 'border-red-500 focus:border-red-500 focus:ring-red-200';
    if (value && !error) return 'border-green-500 focus:border-green-500 focus:ring-green-200';
    return 'border-gray-300 focus:border-blue-500 focus:ring-blue-200';
  };

  return (
    <div className='space-y-2'>
      <label
        htmlFor={id}
        className={`block text-sm font-medium ${
          error ? 'text-red-700' : 'text-gray-700'
        } ${field.required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}`}
      >
        {field.label}
      </label>

      <textarea
        id={id}
        name={field.name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.placeholder}
        disabled={disabled}
        required={field.required}
        rows={rows}
        className={`
          block w-full px-3 py-2 text-sm rounded-md transition-all duration-200 resize-vertical
          ${getValidationClasses()}
          ${disabled ? 'bg-gray-50 cursor-not-allowed' : 'bg-white'}
          focus:outline-none focus:ring-2
          ${className}
        `}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={`${error ? errorId : ''} ${maxLength ? counterId : ''}`}
        minLength={field.validation?.minLength}
        maxLength={maxLength}
        {...props}
      />

      <div className='flex justify-between items-center'>
        {error && (
          <div id={errorId} className='flex items-center text-sm text-red-600' role='alert'>
            <AlertCircle className='h-4 w-4 mr-1 flex-shrink-0' />
            <span>{error}</span>
          </div>
        )}
        {maxLength && (
          <div
            id={counterId}
            className={`text-xs ml-auto ${
              remainingChars && remainingChars < 20 ? 'text-orange-600' : 'text-gray-500'
            }`}
          >
            {remainingChars} characters remaining
          </div>
        )}
      </div>
    </div>
  );
}

// Form validation utilities
export function validateField(field: FormField, value: string): string | null {
  // Required validation
  if (field.required && (!value || value.trim() === '')) {
    return `${field.label} is required`;
  }

  // Skip further validation if field is empty and not required
  if (!value || value.trim() === '') {
    return null;
  }

  const { validation } = field;
  if (!validation) return null;

  // Length validation
  if (validation.minLength && value.length < validation.minLength) {
    return `${field.label} must be at least ${validation.minLength} characters`;
  }
  if (validation.maxLength && value.length > validation.maxLength) {
    return `${field.label} must be no more than ${validation.maxLength} characters`;
  }

  // Pattern validation
  if (validation.pattern && !validation.pattern.test(value)) {
    if (field.type === 'email') {
      return 'Please enter a valid email address';
    }
    return `${field.label} format is invalid`;
  }

  // Custom validation
  if (validation.custom) {
    const result = validation.custom(value);
    if (typeof result === 'string') {
      return result;
    }
    if (result === false) {
      return `${field.label} is invalid`;
    }
  }

  return null;
}

// Form submission with accessibility announcements
export function useFormValidation(fields: FormField[]) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const setValue = (name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};
    let hasErrors = false;

    fields.forEach((field) => {
      const error = validateField(field, values[field.name] || '');
      if (error) {
        newErrors[field.name] = error;
        hasErrors = true;
      }
    });

    setErrors(newErrors);

    // Announce validation results to screen readers
    if (hasErrors) {
      const errorCount = Object.keys(newErrors).length;
      const announcement = `Form validation failed. ${errorCount} field${errorCount > 1 ? 's' : ''} need${errorCount === 1 ? 's' : ''} attention.`;
      announceToScreenReader(announcement);
    }

    return !hasErrors;
  };

  const handleSubmit = async (onSubmit: (values: Record<string, string>) => Promise<void>) => {
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      await onSubmit(values);
      announceToScreenReader('Form submitted successfully');
    } catch (error) {
      announceToScreenReader('Form submission failed. Please try again.');
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    values,
    errors,
    isSubmitting,
    setValue,
    validateForm,
    handleSubmit,
  };
}

// Screen reader announcement utility
function announceToScreenReader(message: string) {
  const announcement = document.createElement('div');
  announcement.setAttribute('aria-live', 'polite');
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;
  document.body.appendChild(announcement);
  setTimeout(() => document.body.removeChild(announcement), 1000);
}
