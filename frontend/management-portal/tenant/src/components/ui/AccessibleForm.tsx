/**
 * Accessible Form Components
 * Wraps @dotmac/primitives components with tenant-specific styling and accessibility enhancements
 */

import { Button, Input, Checkbox } from '@dotmac/primitives';
import type { ButtonProps } from '@dotmac/primitives';
import { useState } from 'react';
import { Eye, EyeOff, AlertCircle, CheckCircle, Info, X } from 'lucide-react';
import { clsx } from 'clsx';

// Extend Button props for accessible button
interface AccessibleButtonProps extends Omit<ButtonProps, 'variant'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  isLoading?: boolean;
  loadingText?: string;
}

export function AccessibleButton({
  variant = 'primary',
  isLoading,
  loadingText,
  children,
  disabled,
  className,
  ...props
}: AccessibleButtonProps) {
  const variantMap = {
    primary: 'default',
    secondary: 'secondary',
    ghost: 'ghost',
    destructive: 'destructive',
  } as const;

  return (
    <Button
      variant={variantMap[variant]}
      disabled={disabled || isLoading}
      className={clsx(
        'focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all',
        className
      )}
      {...props}
    >
      {isLoading ? loadingText || 'Loading...' : children}
    </Button>
  );
}

// Input component with accessibility enhancements
interface AccessibleInputProps {
  id: string;
  name: string;
  type?: string;
  label: string;
  description?: string;
  placeholder?: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  required?: boolean;
  autoComplete?: string;
  error?: string;
  showPasswordToggle?: boolean;
}

export function AccessibleInput({
  id,
  name,
  type = 'text',
  label,
  description,
  placeholder,
  value,
  onChange,
  disabled,
  required,
  autoComplete,
  error,
  showPasswordToggle,
  ...props
}: AccessibleInputProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const inputType = type === 'password' && showPassword ? 'text' : type;
  const descriptionId = description ? `${id}-description` : undefined;
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className='space-y-1'>
      <label
        htmlFor={id}
        className={clsx(
          'block text-sm font-medium transition-colors',
          error ? 'text-red-700' : 'text-gray-700',
          isFocused && !error && 'text-blue-700'
        )}
      >
        {label}
        {required && (
          <span className='text-red-500 ml-1' aria-label='required'>
            *
          </span>
        )}
      </label>

      {description && (
        <p id={descriptionId} className='text-sm text-gray-600'>
          {description}
        </p>
      )}

      <div className='relative'>
        <Input
          id={id}
          name={name}
          type={inputType}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          disabled={disabled}
          required={required}
          autoComplete={autoComplete}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          aria-describedby={clsx(descriptionId, errorId).trim() || undefined}
          aria-invalid={error ? 'true' : 'false'}
          className={clsx(
            'w-full transition-colors',
            error && 'border-red-300 focus:border-red-500 focus:ring-red-200',
            showPasswordToggle && 'pr-10'
          )}
          {...props}
        />

        {showPasswordToggle && type === 'password' && (
          <button
            type='button'
            className='absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600 transition-colors'
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        )}
      </div>

      {error && (
        <p id={errorId} className='text-sm text-red-600 flex items-center gap-1' role='alert'>
          <AlertCircle size={14} />
          {error}
        </p>
      )}
    </div>
  );
}

// Checkbox component with accessibility enhancements
interface AccessibleCheckboxProps {
  id: string;
  name: string;
  label: string;
  description?: string;
  checked: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  required?: boolean;
}

export function AccessibleCheckbox({
  id,
  name,
  label,
  description,
  checked,
  onChange,
  disabled,
  required,
}: AccessibleCheckboxProps) {
  const descriptionId = description ? `${id}-description` : undefined;

  return (
    <div className='flex items-start gap-3'>
      <Checkbox
        id={id}
        name={name}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        required={required}
        aria-describedby={descriptionId}
        className='mt-0.5'
      />
      <div className='flex-1'>
        <label
          htmlFor={id}
          className={clsx(
            'text-sm font-medium cursor-pointer transition-colors',
            disabled ? 'text-gray-400' : 'text-gray-700 hover:text-gray-900'
          )}
        >
          {label}
          {required && (
            <span className='text-red-500 ml-1' aria-label='required'>
              *
            </span>
          )}
        </label>
        {description && (
          <p id={descriptionId} className='text-sm text-gray-600 mt-1'>
            {description}
          </p>
        )}
      </div>
    </div>
  );
}

// Alert component with accessibility enhancements
interface AccessibleAlertProps {
  type: 'success' | 'error' | 'warning' | 'info';
  children: React.ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
  className?: string;
}

export function AccessibleAlert({
  type,
  children,
  dismissible,
  onDismiss,
  className,
}: AccessibleAlertProps) {
  const typeConfig = {
    success: {
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      textColor: 'text-green-800',
      icon: CheckCircle,
      iconColor: 'text-green-400',
    },
    error: {
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-800',
      icon: AlertCircle,
      iconColor: 'text-red-400',
    },
    warning: {
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      textColor: 'text-yellow-800',
      icon: AlertCircle,
      iconColor: 'text-yellow-400',
    },
    info: {
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      textColor: 'text-blue-800',
      icon: Info,
      iconColor: 'text-blue-400',
    },
  };

  const config = typeConfig[type];
  const Icon = config.icon;

  return (
    <div
      className={clsx('rounded-md border p-4', config.bgColor, config.borderColor, className)}
      role={type === 'error' ? 'alert' : 'status'}
      aria-live={type === 'error' ? 'assertive' : 'polite'}
    >
      <div className='flex'>
        <div className='flex-shrink-0'>
          <Icon className={clsx('h-5 w-5', config.iconColor)} />
        </div>
        <div className={clsx('ml-3 flex-1', config.textColor)}>{children}</div>
        {dismissible && onDismiss && (
          <div className='ml-auto pl-3'>
            <div className='-mx-1.5 -my-1.5'>
              <button
                type='button'
                className={clsx(
                  'inline-flex rounded-md p-1.5 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                  config.textColor,
                  'hover:bg-black/5 focus:ring-black/20'
                )}
                onClick={onDismiss}
                aria-label='Dismiss alert'
              >
                <X className='h-5 w-5' />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
