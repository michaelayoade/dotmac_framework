/**
 * Reusable Form Components
 * Design system form components with validation and accessibility
 */

'use client';

import React, { forwardRef, useId, type ReactNode } from 'react';
import { Eye, EyeOff, AlertCircle, CheckCircle, Info } from 'lucide-react';
import { cn, variantUtils, a11yUtils } from '../../design-system/utils';
import { useFieldErrors } from '../../hooks/useValidatedForm';
// Import the universal file upload component
import { FileUpload, useFileUpload } from '@dotmac/file-system';

// Base form field wrapper
interface FormFieldProps {
  children: ReactNode;
  label?: string;
  description?: string;
  error?: string | string[];
  required?: boolean;
  className?: string;
  disabled?: boolean;
}

export function FormField({
  children,
  label,
  description,
  error,
  required,
  className,
  disabled
}: FormFieldProps) {
  const id = useId();
  const hasError = Boolean(error && (Array.isArray(error) ? error.length > 0 : error));
  const errorMessage = Array.isArray(error) ? error.join(', ') : error;

  return (
    <div className={cn('space-y-2', className)}>
      {label && (
        <label
          htmlFor={id}
          className={cn(
            'block text-sm font-medium',
            disabled ? 'text-gray-400' : 'text-gray-700',
            hasError && 'text-red-700'
          )}
        >
          {label}
          {required && (
            <span className="text-red-500 ml-1" aria-label="required">*</span>
          )}
        </label>
      )}

      {description && (
        <p className="text-sm text-gray-500" id={`${id}-description`}>
          {description}
        </p>
      )}

      <div className="relative">
        {React.cloneElement(children as React.ReactElement, {
          id,
          'aria-describedby': cn(
            description && `${id}-description`,
            hasError && `${id}-error`
          ),
          'aria-invalid': hasError,
          disabled,
        })}
      </div>

      {hasError && (
        <div className="flex items-start space-x-2 text-sm text-red-600" id={`${id}-error`}>
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
}

// Input component
interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  variant?: 'default' | 'error';
  size?: 'sm' | 'base' | 'lg';
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant = 'default', size = 'base', leftIcon, rightIcon, error, type, ...props }, ref) => {
    const inputVariant = error ? 'error' : variant;

    return (
      <div className="relative">
        {leftIcon && (
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
            {leftIcon}
          </div>
        )}

        <input
          type={type}
          ref={ref}
          className={cn(
            // Base styles
            'w-full rounded-lg border transition-colors duration-200',
            'placeholder:text-gray-400 disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
            // Focus styles
            a11yUtils.focusRing,
            // Size variants
            variantUtils.input.size[size],
            // Color variants
            variantUtils.input.variant[inputVariant],
            // Icon padding
            leftIcon && 'pl-10',
            rightIcon && 'pr-10',
            className
          )}
          {...props}
        />

        {rightIcon && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400">
            {rightIcon}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

// Password input with toggle visibility
interface PasswordInputProps extends Omit<InputProps, 'type' | 'rightIcon'> {
  showToggle?: boolean;
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ showToggle = true, ...props }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false);

    const togglePassword = () => {
      setShowPassword(!showPassword);
    };

    return (
      <Input
        ref={ref}
        type={showPassword ? 'text' : 'password'}
        rightIcon={
          showToggle ? (
            <button
              type="button"
              onClick={togglePassword}
              className="text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600"
              tabIndex={-1}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          ) : undefined
        }
        {...props}
      />
    );
  }
);

PasswordInput.displayName = 'PasswordInput';

// Textarea component
interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  variant?: 'default' | 'error';
  resize?: 'none' | 'both' | 'horizontal' | 'vertical';
  error?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant = 'default', resize = 'vertical', error, ...props }, ref) => {
    const textareaVariant = error ? 'error' : variant;

    const resizeClass = {
      none: 'resize-none',
      both: 'resize',
      horizontal: 'resize-x',
      vertical: 'resize-y',
    };

    return (
      <textarea
        ref={ref}
        className={cn(
          // Base styles
          'w-full rounded-lg border px-3 py-2 text-base transition-colors duration-200',
          'placeholder:text-gray-400 disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
          'min-h-[80px]',
          // Focus styles
          a11yUtils.focusRing,
          // Color variants
          variantUtils.input.variant[textareaVariant],
          // Resize
          resizeClass[resize],
          className
        )}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';

// Select component
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  variant?: 'default' | 'error';
  size?: 'sm' | 'base' | 'lg';
  placeholder?: string;
  error?: boolean;
  options?: Array<{ value: string; label: string; disabled?: boolean }>;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, variant = 'default', size = 'base', error, options, placeholder, children, ...props }, ref) => {
    const selectVariant = error ? 'error' : variant;

    return (
      <select
        ref={ref}
        className={cn(
          // Base styles
          'w-full rounded-lg border bg-white transition-colors duration-200',
          'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
          // Focus styles
          a11yUtils.focusRing,
          // Size variants
          variantUtils.input.size[size],
          // Color variants
          variantUtils.input.variant[selectVariant],
          className
        )}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options?.map((option) => (
          <option
            key={option.value}
            value={option.value}
            disabled={option.disabled}
          >
            {option.label}
          </option>
        ))}
        {children}
      </select>
    );
  }
);

Select.displayName = 'Select';

// Checkbox component
interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  description?: string;
  error?: boolean;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, description, error, ...props }, ref) => {
    const id = useId();

    return (
      <div className="flex items-start space-x-3">
        <div className="flex items-center h-5">
          <input
            id={id}
            ref={ref}
            type="checkbox"
            className={cn(
              'h-4 w-4 rounded border-gray-300 text-primary-600 transition-colors duration-200',
              'focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
              'disabled:cursor-not-allowed disabled:opacity-50',
              error && 'border-red-300 text-red-600 focus:ring-red-500',
              className
            )}
            {...props}
          />
        </div>

        {(label || description) && (
          <div className="text-sm">
            {label && (
              <label
                htmlFor={id}
                className={cn(
                  'font-medium',
                  error ? 'text-red-700' : 'text-gray-700',
                  'cursor-pointer'
                )}
              >
                {label}
              </label>
            )}
            {description && (
              <p className="text-gray-500 mt-1">{description}</p>
            )}
          </div>
        )}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

// Radio group component
interface RadioOption {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
}

interface RadioGroupProps {
  name: string;
  value?: string;
  onChange?: (value: string) => void;
  options: RadioOption[];
  error?: boolean;
  disabled?: boolean;
  className?: string;
}

export function RadioGroup({
  name,
  value,
  onChange,
  options,
  error,
  disabled,
  className
}: RadioGroupProps) {
  return (
    <div className={cn('space-y-3', className)} role="radiogroup">
      {options.map((option) => {
        const id = `${name}-${option.value}`;
        const isChecked = value === option.value;
        const isDisabled = disabled || option.disabled;

        return (
          <div key={option.value} className="flex items-start space-x-3">
            <div className="flex items-center h-5">
              <input
                id={id}
                name={name}
                type="radio"
                value={option.value}
                checked={isChecked}
                onChange={(e) => onChange?.(e.target.value)}
                disabled={isDisabled}
                className={cn(
                  'h-4 w-4 border-gray-300 text-primary-600 transition-colors duration-200',
                  'focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
                  'disabled:cursor-not-allowed disabled:opacity-50',
                  error && 'border-red-300 text-red-600 focus:ring-red-500'
                )}
              />
            </div>

            <div className="text-sm">
              <label
                htmlFor={id}
                className={cn(
                  'font-medium cursor-pointer',
                  error ? 'text-red-700' : 'text-gray-700',
                  isDisabled && 'text-gray-400 cursor-not-allowed'
                )}
              >
                {option.label}
              </label>
              {option.description && (
                <p className="text-gray-500 mt-1">{option.description}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// File input component - now wraps the universal FileUpload
interface FileInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  onFileSelect?: (files: FileList | null) => void;
  acceptedTypes?: string[];
  maxSize?: number; // in bytes
  error?: boolean;
  preview?: boolean;
}

export const FileInput = forwardRef<HTMLInputElement, FileInputProps>(
  ({ className, onFileSelect, acceptedTypes, maxSize, error, preview, ...props }, ref) => {
    const handleFilesAdded = (fileItems: any[]) => {
      // Convert FileItems back to FileList for compatibility
      const files = fileItems.map(item => {
        // This is a simplified conversion - in real implementation,
        // you might want to maintain the original File objects
        return new File([''], item.name, { type: item.type });
      });

      // Create a mock FileList
      const fileList = {
        length: files.length,
        item: (index: number) => files[index],
        ...files
      } as unknown as FileList;

      onFileSelect?.(fileList);
    };

    return (
      <FileUpload
        options={{
          accept: acceptedTypes,
          maxSize,
          multiple: props.multiple,
          generateThumbnails: preview
        }}
        onFilesAdded={handleFilesAdded}
        variant="dropzone"
        showPreview={preview}
        disabled={props.disabled}
        className={className}
      />
    );
  }
);

FileInput.displayName = 'FileInput';

// Enhanced file upload hook for forms
export function useFormFileUpload(options?: {
  maxSize?: number;
  accept?: string[];
  multiple?: boolean;
  onUpload?: (file: File) => Promise<any>;
}) {
  return useFileUpload({
    maxSize: options?.maxSize || 10 * 1024 * 1024, // 10MB default
    accept: options?.accept || [],
    multiple: options?.multiple || false,
    generateThumbnails: true,
    uploadFunction: options?.onUpload
  });
}

// Form validation message component
interface ValidationMessageProps {
  type: 'error' | 'success' | 'info';
  message: string;
  className?: string;
}

export function ValidationMessage({ type, message, className }: ValidationMessageProps) {
  const icons = {
    error: AlertCircle,
    success: CheckCircle,
    info: Info,
  };

  const styles = {
    error: 'text-red-600 bg-red-50 border-red-200',
    success: 'text-green-600 bg-green-50 border-green-200',
    info: 'text-blue-600 bg-blue-50 border-blue-200',
  };

  const Icon = icons[type];

  return (
    <div className={cn('flex items-center space-x-2 p-3 rounded-lg border', styles[type], className)}>
      <Icon className="w-4 h-4 flex-shrink-0" />
      <span className="text-sm">{message}</span>
    </div>
  );
}
