import React, { forwardRef, ReactNode } from 'react';
import { ExclamationCircleIcon } from '@heroicons/react/24/outline';

// Form Field Base Component
interface FormFieldProps {
  label?: string;
  error?: string;
  required?: boolean;
  hint?: string;
  className?: string;
  children: ReactNode;
}

export function FormField({ label, error, required, hint, className = '', children }: FormFieldProps) {
  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label className="label">
          {label}
          {required && <span className="text-danger-500 ml-1">*</span>}
        </label>
      )}
      
      {children}
      
      {error && (
        <div className="flex items-center space-x-1 text-danger-600 text-sm">
          <ExclamationCircleIcon className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
      
      {hint && !error && (
        <p className="text-sm text-gray-500">{hint}</p>
      )}
    </div>
  );
}

// Enhanced Input Component
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  leftIcon?: React.ComponentType<{ className?: string }>;
  rightIcon?: React.ComponentType<{ className?: string }>;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error, leftIcon: LeftIcon, rightIcon: RightIcon, className = '', ...props }, ref) => {
    const inputClasses = `
      input 
      ${error ? 'input-error' : ''}
      ${LeftIcon ? 'pl-10' : ''}
      ${RightIcon ? 'pr-10' : ''}
      ${className}
    `;

    return (
      <div className="relative">
        {LeftIcon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <LeftIcon className="h-5 w-5 text-gray-400" />
          </div>
        )}
        
        <input
          ref={ref}
          className={inputClasses}
          aria-invalid={error ? 'true' : 'false'}
          {...props}
        />
        
        {RightIcon && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <RightIcon className="h-5 w-5 text-gray-400" />
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

// Enhanced Textarea Component
interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string;
  resize?: 'none' | 'both' | 'horizontal' | 'vertical';
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ error, resize = 'vertical', className = '', ...props }, ref) => {
    const resizeClasses = {
      none: 'resize-none',
      both: 'resize',
      horizontal: 'resize-x',
      vertical: 'resize-y',
    };

    return (
      <textarea
        ref={ref}
        className={`input ${error ? 'input-error' : ''} ${resizeClasses[resize]} ${className}`}
        aria-invalid={error ? 'true' : 'false'}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';

// Enhanced Select Component
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: string;
  options: Array<{ value: string; label: string; disabled?: boolean }>;
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ error, options, placeholder, className = '', ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={`input ${error ? 'input-error' : ''} ${className}`}
        aria-invalid={error ? 'true' : 'false'}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }
);

Select.displayName = 'Select';

// Checkbox Component
interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  description?: string;
  error?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, error, className = '', ...props }, ref) => {
    return (
      <div className="space-y-1">
        <div className="flex items-start">
          <input
            type="checkbox"
            ref={ref}
            className={`
              mt-1 h-4 w-4 text-primary-600 border-gray-300 rounded
              focus:ring-primary-500 focus:border-primary-500
              ${error ? 'border-danger-300' : ''}
              ${className}
            `}
            aria-invalid={error ? 'true' : 'false'}
            {...props}
          />
          {(label || description) && (
            <div className="ml-3">
              {label && (
                <label className="text-sm font-medium text-gray-700">
                  {label}
                </label>
              )}
              {description && (
                <p className="text-sm text-gray-500">
                  {description}
                </p>
              )}
            </div>
          )}
        </div>
        
        {error && (
          <div className="flex items-center space-x-1 text-danger-600 text-sm">
            <ExclamationCircleIcon className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

// Radio Group Component
interface RadioOption {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
}

interface RadioGroupProps {
  name: string;
  options: RadioOption[];
  value?: string;
  onChange?: (value: string) => void;
  error?: string;
  layout?: 'vertical' | 'horizontal';
}

export function RadioGroup({ 
  name, 
  options, 
  value, 
  onChange, 
  error, 
  layout = 'vertical' 
}: RadioGroupProps) {
  const layoutClasses = layout === 'horizontal' ? 'flex space-x-6' : 'space-y-3';

  return (
    <fieldset>
      <div className={layoutClasses}>
        {options.map((option) => (
          <div key={option.value} className="flex items-start">
            <input
              id={`${name}-${option.value}`}
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={(e) => onChange?.(e.target.value)}
              disabled={option.disabled}
              className={`
                mt-1 h-4 w-4 text-primary-600 border-gray-300
                focus:ring-primary-500 focus:border-primary-500
                ${error ? 'border-danger-300' : ''}
              `}
              aria-invalid={error ? 'true' : 'false'}
            />
            <div className="ml-3">
              <label 
                htmlFor={`${name}-${option.value}`}
                className="text-sm font-medium text-gray-700"
              >
                {option.label}
              </label>
              {option.description && (
                <p className="text-sm text-gray-500">
                  {option.description}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {error && (
        <div className="mt-1 flex items-center space-x-1 text-danger-600 text-sm">
          <ExclamationCircleIcon className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
    </fieldset>
  );
}

// Form Actions Component
interface FormActionsProps {
  children: ReactNode;
  align?: 'left' | 'center' | 'right';
  spacing?: 'tight' | 'normal' | 'wide';
  className?: string;
}

export function FormActions({ 
  children, 
  align = 'right', 
  spacing = 'normal',
  className = '' 
}: FormActionsProps) {
  const alignClasses = {
    left: 'justify-start',
    center: 'justify-center',
    right: 'justify-end',
  };

  const spacingClasses = {
    tight: 'space-x-2',
    normal: 'space-x-3',
    wide: 'space-x-4',
  };

  return (
    <div className={`
      flex items-center ${alignClasses[align]} ${spacingClasses[spacing]}
      pt-6 border-t border-gray-200 ${className}
    `}>
      {children}
    </div>
  );
}

// Form Section Component
interface FormSectionProps {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

export function FormSection({ title, description, children, className = '' }: FormSectionProps) {
  return (
    <div className={`space-y-6 ${className}`}>
      {(title || description) && (
        <div className="border-b border-gray-200 pb-4">
          {title && (
            <h3 className="text-lg font-medium text-gray-900">
              {title}
            </h3>
          )}
          {description && (
            <p className="mt-1 text-sm text-gray-600">
              {description}
            </p>
          )}
        </div>
      )}
      
      <div className="space-y-6">
        {children}
      </div>
    </div>
  );
}