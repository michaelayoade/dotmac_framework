'use client';

import type { ReactNode } from 'react';

import { useFormSubmission, useFormValidation } from '../hooks/useFormValidation';
import type { FormValidationConfig } from '../utils/formValidation';

export interface ValidatedFormProps {
  initialValues?: Record<string, unknown>;
  validationConfig: FormValidationConfig;
  onSubmit: (data: Record<string, unknown>) => Promise<void> | void;
  onSuccess?: (data: unknown) => void;
  onError?: (error: unknown) => void;
  resetOnSuccess?: boolean;
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
  debounceTime?: number;
  children: (formProps: ValidatedFormChildProps) => ReactNode;
  className?: string;
}

export interface ValidatedFormChildProps {
  formData: Record<string, unknown>;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
  isValid: boolean;
  isValidating: boolean;
  isSubmitting: boolean;
  submitError: string | null;
  submitSuccess: boolean;
  setValue: (field: string, value: unknown) => void;
  setValues: (values: Record<string, unknown>) => void;
  validateField: (field: string) => Promise<void>;
  validateForm: () => Promise<unknown>;
  resetForm: (initialValues?: Record<string, unknown>) => void;
  getFieldProps: (field: string) => any;
  setTouched: (field: string, isTouched?: boolean) => void;
}

export function ValidatedForm({
  initialValues = {
    // Implementation pending
  },
  validationConfig,
  onSubmit,
  onSuccess,
  onError,
  resetOnSuccess = false,
  validateOnChange = true,
  validateOnBlur = true,
  debounceTime = 300,
  children,
  className,
}: ValidatedFormProps) {
  const id = useId();
  const formValidation = useFormValidation(initialValues, {
    validationConfig,
    validateOnChange,
    validateOnBlur,
    debounceTime,
  });

  const formSubmission = useFormSubmission({
    onSuccess: (data) => {
      if (resetOnSuccess) {
        formValidation.resetForm();
      }
      onSuccess?.(data);
    },
    onError,
  });

  const handleSubmit = formValidation.handleSubmit(async (data) => {
    await formSubmission.submit(() => onSubmit(data));
  });

  const childProps: ValidatedFormChildProps = {
    ...formValidation,
    isSubmitting: formSubmission.isSubmitting,
    submitError: formSubmission.submitError,
    submitSuccess: formSubmission.submitSuccess,
  };

  return (
    <form onSubmit={handleSubmit} className={className} noValidate>
      {children(childProps)}
    </form>
  );
}

// Validation message component
export interface ValidationMessageProps {
  error?: string;
  fieldId?: string;
  className?: string;
}

export function ValidationMessage({ error, fieldId, className = '' }: ValidationMessageProps) {
  const id = useId();
  if (!error) {
    return null;
  }

  return (
    <p
      id={fieldId ? `${fieldId}-error` : undefined}
      className={`mt-1 text-red-600 text-sm ${className}`}
      role='alert'
    >
      {error}
    </p>
  );
}

// Form field wrapper component
export interface FormFieldProps {
  label: string;
  fieldId: string;
  required?: boolean;
  error?: string;
  helpText?: string;
  children: ReactNode;
  className?: string;
}

export function FormField({
  label,
  fieldId,
  required = false,
  error,
  helpText,
  children,
  className = '',
}: FormFieldProps) {
  const id = useId();
  return (
    <div className={`space-y-1 ${className}`}>
      <label htmlFor={fieldId} className='block font-medium text-gray-700 text-sm'>
        {label}
        {required ? (
          <span className='ml-1 text-red-500' aria-label='required'>
            *
          </span>
        ) : null}
      </label>

      {children}

      {error ? <ValidationMessage error={error} fieldId={fieldId} /> : null}

      {helpText && !error ? <p className='text-gray-500 text-sm'>{helpText}</p> : null}
    </div>
  );
}

// Success message component
export interface SuccessMessageProps {
  message: string;
  onDismiss?: () => void;
  className?: string;
}

export function SuccessMessage({ message, onDismiss, className = '' }: SuccessMessageProps) {
  const id = useId();
  return (
    <div className={`rounded-md border border-green-200 bg-green-50 p-4 ${className}`}>
      <div className='flex'>
        <div className='flex-shrink-0'>
          <svg
            aria-label='icon'
            className='h-5 w-5 text-green-400'
            viewBox='0 0 20 20'
            fill='currentColor'
          >
            <title>Icon</title>
            <path
              fillRule='evenodd'
              d='M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z'
              clipRule='evenodd'
            />
          </svg>
        </div>
        <div className='ml-3'>
          <p className='font-medium text-green-800 text-sm'>{message}</p>
        </div>
        {onDismiss ? (
          <div className='ml-auto pl-3'>
            <div className='-mx-1.5 -my-1.5'>
              <button
                type='button'
                onClick={onDismiss}
                onKeyDown={(e) => e.key === 'Enter' && onDismiss}
                className='inline-flex rounded-md bg-green-50 p-1.5 text-green-500 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-green-600 focus:ring-offset-2 focus:ring-offset-green-50'
              >
                <span className='sr-only'>Dismiss</span>
                <svg aria-label='icon' className='h-3 w-3' viewBox='0 0 20 20' fill='currentColor'>
                  <title>Icon</title>
                  <path
                    fillRule='evenodd'
                    d='M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z'
                    clipRule='evenodd'
                  />
                </svg>
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

// Error message component
export interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorMessage({
  title = 'Error',
  message,
  onRetry,
  onDismiss,
  className = '',
}: ErrorMessageProps) {
  const id = useId();
  return (
    <div className={`rounded-md border border-red-200 bg-red-50 p-4 ${className}`}>
      <div className='flex'>
        <div className='flex-shrink-0'>
          <svg
            aria-label='icon'
            className='h-5 w-5 text-red-400'
            viewBox='0 0 20 20'
            fill='currentColor'
          >
            <title>Icon</title>
            <path
              fillRule='evenodd'
              d='M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z'
              clipRule='evenodd'
            />
          </svg>
        </div>
        <div className='ml-3 flex-1'>
          <h3 className='font-medium text-red-800 text-sm'>{title}</h3>
          <p className='mt-2 text-red-700 text-sm'>{message}</p>
          {onRetry ? (
            <div className='mt-4'>
              <button
                type='button'
                onClick={onRetry}
                onKeyDown={(e) => e.key === 'Enter' && onRetry}
                className='rounded-md bg-red-100 px-2 py-1 font-medium text-red-800 text-sm hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2'
              >
                Try Again
              </button>
            </div>
          ) : null}
        </div>
        {onDismiss ? (
          <div className='ml-auto pl-3'>
            <div className='-mx-1.5 -my-1.5'>
              <button
                type='button'
                onClick={onDismiss}
                onKeyDown={(e) => e.key === 'Enter' && onDismiss}
                className='inline-flex rounded-md bg-red-50 p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50'
              >
                <span className='sr-only'>Dismiss</span>
                <svg aria-label='icon' className='h-3 w-3' viewBox='0 0 20 20' fill='currentColor'>
                  <title>Icon</title>
                  <path
                    fillRule='evenodd'
                    d='M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z'
                    clipRule='evenodd'
                  />
                </svg>
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
