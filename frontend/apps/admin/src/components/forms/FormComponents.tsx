/**
 * Reusable Form Components
 * Design system form components with validation and accessibility
 */

'use client';

import React, { forwardRef, useId, type ReactNode } from 'react';
import { Eye, EyeOff, AlertCircle, CheckCircle, Info, X } from 'lucide-react';
import { cn, variantUtils, a11yUtils } from '../../design-system/utils';
import { useFieldErrors } from '../../hooks/useValidatedForm';

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

// File input component
interface FileInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  onFileSelect?: (files: FileList | null) => void;
  acceptedTypes?: string[];
  maxSize?: number; // in bytes
  error?: boolean;
  preview?: boolean;
}

export const FileInput = forwardRef<HTMLInputElement, FileInputProps>(
  ({ className, onFileSelect, acceptedTypes, maxSize, error, preview, onChange, ...props }, ref) => {
    const [selectedFiles, setSelectedFiles] = React.useState<FileList | null>(null);
    const [dragActive, setDragActive] = React.useState(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      setSelectedFiles(files);
      onFileSelect?.(files);
      onChange?.(e);
    };

    const handleDrag = (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.type === 'dragenter' || e.type === 'dragover') {
        setDragActive(true);
      } else if (e.type === 'dragleave') {
        setDragActive(false);
      }
    };

    const handleDrop = (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      
      const files = e.dataTransfer.files;
      setSelectedFiles(files);
      onFileSelect?.(files);
    };

    const formatFileSize = (bytes: number) => {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
      <div className="space-y-3">
        <div
          className={cn(
            'relative border-2 border-dashed rounded-lg p-6 text-center transition-colors duration-200',
            dragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300',
            error && 'border-red-300 bg-red-50',
            'hover:border-primary-400 hover:bg-primary-50',
            className
          )}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={ref}
            type="file"
            onChange={handleChange}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            accept={acceptedTypes?.join(',')}
            {...props}
          />
          
          <div className="space-y-2">
            <div className="text-gray-600">
              <svg className="w-8 h-8 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-sm text-gray-600">
              <span className="font-medium text-primary-600 hover:text-primary-500">
                Click to upload
              </span>
              {' or drag and drop'}
            </p>
            {acceptedTypes && (
              <p className="text-xs text-gray-500">
                {acceptedTypes.join(', ')}
              </p>
            )}
            {maxSize && (
              <p className="text-xs text-gray-500">
                Max size: {formatFileSize(maxSize)}
              </p>
            )}
          </div>
        </div>

        {selectedFiles && selectedFiles.length > 0 && (
          <div className="space-y-2">
            {Array.from(selectedFiles).map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    // Remove file logic would go here
                  }}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
);

FileInput.displayName = 'FileInput';

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