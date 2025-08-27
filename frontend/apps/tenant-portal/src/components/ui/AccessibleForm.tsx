/**
 * Accessible Form Components
 * WCAG 2.1 AA compliant form elements with comprehensive accessibility features
 */

'use client';

import React, { useState, useEffect, useRef, forwardRef } from 'react';
import { Eye, EyeOff, AlertCircle, CheckCircle, Info } from 'lucide-react';
import { generateId, announceToScreenReader } from '@/lib/accessibility';

// ============================================================================
// BASE FORM FIELD COMPONENT
// ============================================================================

interface FormFieldProps {
  id?: string;
  label: string;
  description?: string;
  error?: string;
  success?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function FormField({
  id: providedId,
  label,
  description,
  error,
  success,
  required = false,
  children,
  className = '',
}: FormFieldProps) {
  const id = providedId || generateId('field');
  const descriptionId = description ? `${id}-description` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const successId = success ? `${id}-success` : undefined;

  // Announce errors to screen readers
  useEffect(() => {
    if (error) {
      announceToScreenReader(`Error: ${error}`, 'assertive');
    }
  }, [error]);

  // Announce success to screen readers
  useEffect(() => {
    if (success) {
      announceToScreenReader(`Success: ${success}`, 'polite');
    }
  }, [success]);

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Label */}
      <label
        htmlFor={id}
        className={`block text-sm font-medium transition-colors ${
          error
            ? 'text-red-700'
            : success
            ? 'text-green-700'
            : 'text-gray-700 hover:text-gray-900'
        }`}
      >
        {label}
        {required && (
          <span className="ml-1 text-red-500" aria-label="required">
            *
          </span>
        )}
      </label>

      {/* Description */}
      {description && (
        <p
          id={descriptionId}
          className="text-sm text-gray-600"
        >
          {description}
        </p>
      )}

      {/* Form Control */}
      {React.cloneElement(children as React.ReactElement, {
        id,
        required,
        'aria-describedby': [descriptionId, errorId, successId]
          .filter(Boolean)
          .join(' ') || undefined,
        'aria-invalid': error ? 'true' : 'false',
      })}

      {/* Error Message */}
      {error && (
        <div
          id={errorId}
          role="alert"
          aria-live="assertive"
          className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3"
        >
          <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div
          id={successId}
          role="status"
          aria-live="polite"
          className="flex items-start gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md p-3"
        >
          <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
          <span>{success}</span>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// ACCESSIBLE INPUT COMPONENT
// ============================================================================

interface AccessibleInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'id'> {
  id?: string;
  label: string;
  description?: string;
  error?: string;
  success?: string;
  showPasswordToggle?: boolean;
}

export const AccessibleInput = forwardRef<HTMLInputElement, AccessibleInputProps>(
  function AccessibleInput({
    id,
    label,
    description,
    error,
    success,
    type = 'text',
    className = '',
    showPasswordToggle = false,
    ...props
  }, ref) {
    const [showPassword, setShowPassword] = useState(false);
    const [isFocused, setIsFocused] = useState(false);
    
    const inputType = showPasswordToggle ? (showPassword ? 'text' : 'password') : type;
    const isPasswordField = type === 'password' || showPasswordToggle;

    const baseInputClasses = `
      block w-full px-3 py-2 border rounded-md shadow-sm 
      placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-offset-0
      transition-colors duration-200 text-sm
      disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed
      ${isPasswordField ? 'pr-10' : ''}
      ${error 
        ? 'border-red-300 text-red-900 focus:ring-red-500 focus:border-red-500' 
        : success
        ? 'border-green-300 text-green-900 focus:ring-green-500 focus:border-green-500'
        : 'border-gray-300 text-gray-900 focus:ring-blue-500 focus:border-blue-500'
      }
      ${isFocused ? 'ring-2 ring-opacity-50' : ''}
      ${className}
    `.trim().replace(/\s+/g, ' ');

    return (
      <FormField
        id={id}
        label={label}
        description={description}
        error={error}
        success={success}
        required={props.required}
      >
        <div className="relative">
          <input
            ref={ref}
            type={inputType}
            className={baseInputClasses}
            onFocus={(e) => {
              setIsFocused(true);
              props.onFocus?.(e);
            }}
            onBlur={(e) => {
              setIsFocused(false);
              props.onBlur?.(e);
            }}
            {...props}
          />
          
          {/* Password Toggle Button */}
          {showPasswordToggle && (
            <button
              type="button"
              className={`
                absolute inset-y-0 right-0 pr-3 flex items-center
                text-gray-400 hover:text-gray-600 focus:text-gray-600
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-0
                rounded-r-md transition-colors
                ${props.disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}
              `}
              onClick={() => setShowPassword(!showPassword)}
              disabled={props.disabled}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              aria-pressed={showPassword}
              tabIndex={0}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Eye className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          )}
        </div>
      </FormField>
    );
  }
);

// ============================================================================
// ACCESSIBLE BUTTON COMPONENT
// ============================================================================

interface AccessibleButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  loadingText?: string;
  children: React.ReactNode;
}

export const AccessibleButton = forwardRef<HTMLButtonElement, AccessibleButtonProps>(
  function AccessibleButton({
    variant = 'primary',
    size = 'md',
    isLoading = false,
    loadingText,
    className = '',
    children,
    disabled,
    ...props
  }, ref) {
    const baseClasses = `
      inline-flex items-center justify-center font-medium rounded-md
      transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
      disabled:opacity-50 disabled:cursor-not-allowed
    `;

    const variantClasses = {
      primary: `
        bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500
        disabled:hover:bg-blue-600
      `,
      secondary: `
        bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-blue-500
        disabled:hover:bg-white
      `,
      danger: `
        bg-red-600 text-white hover:bg-red-700 focus:ring-red-500
        disabled:hover:bg-red-600
      `,
      ghost: `
        bg-transparent text-blue-600 hover:bg-blue-50 focus:ring-blue-500
        disabled:hover:bg-transparent
      `,
    };

    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
    };

    const buttonClasses = `
      ${baseClasses}
      ${variantClasses[variant]}
      ${sizeClasses[size]}
      ${className}
    `.trim().replace(/\s+/g, ' ');

    return (
      <button
        ref={ref}
        className={buttonClasses}
        disabled={disabled || isLoading}
        aria-disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        <span>
          {isLoading && loadingText ? loadingText : children}
        </span>
        {isLoading && (
          <span className="sr-only">Loading...</span>
        )}
      </button>
    );
  }
);

// ============================================================================
// ACCESSIBLE CHECKBOX COMPONENT
// ============================================================================

interface AccessibleCheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  description?: string;
  error?: string;
}

export const AccessibleCheckbox = forwardRef<HTMLInputElement, AccessibleCheckboxProps>(
  function AccessibleCheckbox({
    id: providedId,
    label,
    description,
    error,
    className = '',
    ...props
  }, ref) {
    const id = providedId || generateId('checkbox');
    const descriptionId = description ? `${id}-description` : undefined;
    const errorId = error ? `${id}-error` : undefined;

    return (
      <div className={`${className}`}>
        <div className="flex items-start">
          <div className="flex items-center h-5">
            <input
              ref={ref}
              id={id}
              type="checkbox"
              className={`
                h-4 w-4 rounded border-gray-300 text-blue-600 
                focus:ring-blue-500 focus:ring-2 focus:ring-offset-0
                transition-colors
                ${error ? 'border-red-300' : ''}
              `}
              aria-describedby={[descriptionId, errorId].filter(Boolean).join(' ') || undefined}
              aria-invalid={error ? 'true' : 'false'}
              {...props}
            />
          </div>
          
          <div className="ml-2">
            <label
              htmlFor={id}
              className={`text-sm font-medium cursor-pointer select-none ${
                error ? 'text-red-700' : 'text-gray-900'
              }`}
            >
              {label}
              {props.required && (
                <span className="ml-1 text-red-500" aria-label="required">
                  *
                </span>
              )}
            </label>
            
            {description && (
              <p
                id={descriptionId}
                className="text-sm text-gray-600 mt-1"
              >
                {description}
              </p>
            )}
            
            {error && (
              <div
                id={errorId}
                role="alert"
                aria-live="assertive"
                className="flex items-start gap-1 text-sm text-red-700 mt-1"
              >
                <AlertCircle className="h-3 w-3 text-red-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
);

// ============================================================================
// ACCESSIBLE ALERT COMPONENT
// ============================================================================

interface AccessibleAlertProps {
  type: 'error' | 'warning' | 'success' | 'info';
  title?: string;
  children: React.ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
  className?: string;
}

export function AccessibleAlert({
  type,
  title,
  children,
  dismissible = false,
  onDismiss,
  className = '',
}: AccessibleAlertProps) {
  const icons = {
    error: AlertCircle,
    warning: AlertCircle,
    success: CheckCircle,
    info: Info,
  };

  const styles = {
    error: {
      container: 'bg-red-50 border-red-200 text-red-800',
      icon: 'text-red-400',
      button: 'text-red-500 hover:text-red-600 focus:ring-red-500',
    },
    warning: {
      container: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      icon: 'text-yellow-400',
      button: 'text-yellow-500 hover:text-yellow-600 focus:ring-yellow-500',
    },
    success: {
      container: 'bg-green-50 border-green-200 text-green-800',
      icon: 'text-green-400',
      button: 'text-green-500 hover:text-green-600 focus:ring-green-500',
    },
    info: {
      container: 'bg-blue-50 border-blue-200 text-blue-800',
      icon: 'text-blue-400',
      button: 'text-blue-500 hover:text-blue-600 focus:ring-blue-500',
    },
  };

  const Icon = icons[type];
  const style = styles[type];

  return (
    <div
      role={type === 'error' ? 'alert' : 'status'}
      aria-live={type === 'error' ? 'assertive' : 'polite'}
      className={`
        border rounded-md p-4 ${style.container} ${className}
      `}
    >
      <div className="flex">
        <div className="flex-shrink-0">
          <Icon className={`h-5 w-5 ${style.icon}`} aria-hidden="true" />
        </div>
        
        <div className="ml-3 flex-1">
          {title && (
            <h3 className="text-sm font-medium mb-1">
              {title}
            </h3>
          )}
          <div className="text-sm">
            {children}
          </div>
        </div>
        
        {dismissible && onDismiss && (
          <div className="ml-auto pl-3">
            <button
              type="button"
              className={`
                inline-flex rounded-md p-1.5 focus:outline-none focus:ring-2 focus:ring-offset-2
                ${style.button}
              `}
              onClick={onDismiss}
              aria-label="Dismiss alert"
            >
              <span className="sr-only">Dismiss</span>
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// LOADING SPINNER COMPONENT
// ============================================================================

interface AccessibleLoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export function AccessibleLoadingSpinner({
  size = 'md',
  className = '',
  label = 'Loading...'
}: AccessibleLoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12'
  };

  return (
    <div
      className={`inline-block animate-spin rounded-full border-2 border-solid border-current border-r-transparent ${sizeClasses[size]} ${className}`}
      role="status"
      aria-label={label}
    >
      <span className="sr-only">{label}</span>
    </div>
  );
}