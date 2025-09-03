/**
 * Secure Form Components
 * All form inputs with built-in validation and sanitization
 */

import React, { useState, useCallback, forwardRef } from 'react';
import { AlertCircle, CheckCircle, Eye, EyeOff } from 'lucide-react';
import {
  validateAndSanitizeInput,
  presetValidators,
  type ValidationResult,
  type ValidationOptions,
} from '../../lib/input-validation';

interface BaseSecureInputProps {
  label?: string;
  helperText?: string;
  required?: boolean;
  className?: string;
  validationOptions?: ValidationOptions;
  onValidationChange?: (result: ValidationResult) => void;
  showValidationState?: boolean;
}

interface SecureInputProps
  extends BaseSecureInputProps,
    Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'onBlur'> {
  value: string;
  onChange: (value: string, isValid: boolean) => void;
  onBlur?: (value: string, isValid: boolean) => void;
}

interface SecureTextareaProps
  extends BaseSecureInputProps,
    Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'onChange' | 'onBlur'> {
  value: string;
  onChange: (value: string, isValid: boolean) => void;
  onBlur?: (value: string, isValid: boolean) => void;
}

/**
 * Secure Input Component with built-in validation
 */
export const SecureInput = forwardRef<HTMLInputElement, SecureInputProps>(
  (
    {
      label,
      helperText,
      required,
      className = '',
      validationOptions,
      onValidationChange,
      showValidationState = true,
      value,
      onChange,
      onBlur,
      type = 'text',
      ...props
    },
    ref
  ) => {
    const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
    const [showPassword, setShowPassword] = useState(false);

    const validateInput = useCallback(
      (inputValue: string) => {
        let result: ValidationResult;

        // Use preset validators for common types
        if (type === 'email') {
          result = presetValidators.email(inputValue);
        } else if (type === 'password') {
          result = presetValidators.password(inputValue);
        } else if (type === 'tel') {
          result = presetValidators.phone(inputValue);
        } else if (type === 'url') {
          result = presetValidators.url(inputValue);
        } else {
          result = validateAndSanitizeInput(inputValue, {
            required,
            ...validationOptions,
          });
        }

        setValidationResult(result);
        onValidationChange?.(result);

        return result;
      },
      [type, required, validationOptions, onValidationChange]
    );

    const handleChange = useCallback(
      (event: React.ChangeEvent<HTMLInputElement>) => {
        const inputValue = event.target.value;
        const result = validateInput(inputValue);
        onChange(result.sanitized, result.isValid);
      },
      [onChange, validateInput]
    );

    const handleBlur = useCallback(
      (event: React.FocusEvent<HTMLInputElement>) => {
        const inputValue = event.target.value;
        const result = validateInput(inputValue);
        onBlur?.(result.sanitized, result.isValid);
      },
      [onBlur, validateInput]
    );

    const inputType = type === 'password' && showPassword ? 'text' : type;
    const hasError = validationResult && !validationResult.isValid;
    const hasWarning = validationResult && validationResult.warnings.length > 0;

    const inputClasses = [
      'block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-1 sm:text-sm',
      hasError
        ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
        : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500',
      className,
    ].join(' ');

    return (
      <div className='space-y-1'>
        {label && (
          <label className='block text-sm font-medium text-gray-700'>
            {label}
            {required && <span className='text-red-500 ml-1'>*</span>}
          </label>
        )}

        <div className='relative'>
          <input
            ref={ref}
            type={inputType}
            value={value}
            onChange={handleChange}
            onBlur={handleBlur}
            className={inputClasses}
            aria-invalid={hasError}
            aria-describedby={
              helperText || validationResult?.errors.length
                ? `${props.id || 'input'}-description`
                : undefined
            }
            {...props}
          />

          {type === 'password' && (
            <button
              type='button'
              className='absolute inset-y-0 right-0 pr-3 flex items-center'
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className='h-4 w-4 text-gray-400' />
              ) : (
                <Eye className='h-4 w-4 text-gray-400' />
              )}
            </button>
          )}

          {showValidationState && validationResult && (
            <div className='absolute inset-y-0 right-0 pr-3 flex items-center'>
              {type !== 'password' &&
                (validationResult.isValid ? (
                  <CheckCircle className='h-4 w-4 text-green-500' />
                ) : (
                  <AlertCircle className='h-4 w-4 text-red-500' />
                ))}
            </div>
          )}
        </div>

        {/* Helper text and validation messages */}
        <div id={`${props.id || 'input'}-description`} className='space-y-1'>
          {helperText && <p className='text-sm text-gray-500'>{helperText}</p>}

          {validationResult?.errors.map((error, index) => (
            <p key={index} className='text-sm text-red-600 flex items-center'>
              <AlertCircle className='h-3 w-3 mr-1' />
              {error}
            </p>
          ))}

          {validationResult?.warnings.map((warning, index) => (
            <p key={index} className='text-sm text-yellow-600 flex items-center'>
              <AlertCircle className='h-3 w-3 mr-1' />
              {warning}
            </p>
          ))}
        </div>
      </div>
    );
  }
);

SecureInput.displayName = 'SecureInput';

/**
 * Secure Textarea Component with built-in validation
 */
export const SecureTextarea = forwardRef<HTMLTextAreaElement, SecureTextareaProps>(
  (
    {
      label,
      helperText,
      required,
      className = '',
      validationOptions,
      onValidationChange,
      showValidationState = true,
      value,
      onChange,
      onBlur,
      ...props
    },
    ref
  ) => {
    const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);

    const validateInput = useCallback(
      (inputValue: string) => {
        const result = validateAndSanitizeInput(inputValue, {
          required,
          ...validationOptions,
        });

        setValidationResult(result);
        onValidationChange?.(result);

        return result;
      },
      [required, validationOptions, onValidationChange]
    );

    const handleChange = useCallback(
      (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        const inputValue = event.target.value;
        const result = validateInput(inputValue);
        onChange(result.sanitized, result.isValid);
      },
      [onChange, validateInput]
    );

    const handleBlur = useCallback(
      (event: React.FocusEvent<HTMLTextAreaElement>) => {
        const inputValue = event.target.value;
        const result = validateInput(inputValue);
        onBlur?.(result.sanitized, result.isValid);
      },
      [onBlur, validateInput]
    );

    const hasError = validationResult && !validationResult.isValid;

    const textareaClasses = [
      'block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-1 sm:text-sm',
      hasError
        ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
        : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500',
      className,
    ].join(' ');

    return (
      <div className='space-y-1'>
        {label && (
          <label className='block text-sm font-medium text-gray-700'>
            {label}
            {required && <span className='text-red-500 ml-1'>*</span>}
          </label>
        )}

        <div className='relative'>
          <textarea
            ref={ref}
            value={value}
            onChange={handleChange}
            onBlur={handleBlur}
            className={textareaClasses}
            aria-invalid={hasError}
            aria-describedby={
              helperText || validationResult?.errors.length
                ? `${props.id || 'textarea'}-description`
                : undefined
            }
            {...props}
          />

          {showValidationState && validationResult && (
            <div className='absolute top-2 right-2'>
              {validationResult.isValid ? (
                <CheckCircle className='h-4 w-4 text-green-500' />
              ) : (
                <AlertCircle className='h-4 w-4 text-red-500' />
              )}
            </div>
          )}
        </div>

        {/* Helper text and validation messages */}
        <div id={`${props.id || 'textarea'}-description`} className='space-y-1'>
          {helperText && <p className='text-sm text-gray-500'>{helperText}</p>}

          {validationResult?.errors.map((error, index) => (
            <p key={index} className='text-sm text-red-600 flex items-center'>
              <AlertCircle className='h-3 w-3 mr-1' />
              {error}
            </p>
          ))}

          {validationResult?.warnings.map((warning, index) => (
            <p key={index} className='text-sm text-yellow-600 flex items-center'>
              <AlertCircle className='h-3 w-3 mr-1' />
              {warning}
            </p>
          ))}
        </div>
      </div>
    );
  }
);

SecureTextarea.displayName = 'SecureTextarea';

/**
 * Secure File Upload Component
 */
interface SecureFileUploadProps {
  label?: string;
  helperText?: string;
  required?: boolean;
  className?: string;
  maxSize?: number; // in bytes
  allowedTypes?: string[];
  allowedExtensions?: string[];
  onValidationChange?: (result: ValidationResult) => void;
  onChange: (file: File | null, isValid: boolean) => void;
  accept?: string;
}

export const SecureFileUpload: React.FC<SecureFileUploadProps> = ({
  label,
  helperText,
  required,
  className = '',
  maxSize = 10 * 1024 * 1024, // 10MB default
  allowedTypes = ['image/jpeg', 'image/png', 'application/pdf', 'text/csv'],
  allowedExtensions = ['jpg', 'jpeg', 'png', 'pdf', 'csv'],
  onValidationChange,
  onChange,
  accept,
  ...props
}) => {
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const validateFile = useCallback(
    (file: File) => {
      const result = {
        isValid: true,
        sanitized: file.name,
        errors: [] as string[],
        warnings: [] as string[],
      };

      // Check file size
      if (maxSize && file.size > maxSize) {
        result.errors.push(`File size exceeds ${Math.round(maxSize / 1024 / 1024)}MB limit`);
        result.isValid = false;
      }

      // Check file type
      if (allowedTypes && !allowedTypes.includes(file.type)) {
        result.errors.push(`File type ${file.type} is not allowed`);
        result.isValid = false;
      }

      // Check file extension
      if (allowedExtensions) {
        const extension = file.name.split('.').pop()?.toLowerCase();
        if (!extension || !allowedExtensions.includes(extension)) {
          result.errors.push(`File extension .${extension || 'unknown'} is not allowed`);
          result.isValid = false;
        }
      }

      // Sanitize filename
      const sanitizedName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_').substring(0, 255);

      if (sanitizedName !== file.name) {
        result.warnings.push('Filename was sanitized for security');
        result.sanitized = sanitizedName;
      }

      return result;
    },
    [maxSize, allowedTypes, allowedExtensions]
  );

  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];

      if (!file) {
        setSelectedFile(null);
        setValidationResult(null);
        onChange(null, !required);
        return;
      }

      const result = validateFile(file);
      setValidationResult(result);
      setSelectedFile(file);
      onValidationChange?.(result);
      onChange(file, result.isValid);
    },
    [validateFile, onChange, onValidationChange, required]
  );

  const hasError = validationResult && !validationResult.isValid;

  return (
    <div className='space-y-2'>
      {label && (
        <label className='block text-sm font-medium text-gray-700'>
          {label}
          {required && <span className='text-red-500 ml-1'>*</span>}
        </label>
      )}

      <div className='mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md'>
        <div className='space-y-1 text-center'>
          <div className='flex text-sm text-gray-600'>
            <label className='relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500'>
              <span>Upload a file</span>
              <input
                type='file'
                className='sr-only'
                onChange={handleFileChange}
                accept={accept || allowedTypes.join(',')}
                {...props}
              />
            </label>
            <p className='pl-1'>or drag and drop</p>
          </div>
          {helperText && <p className='text-xs text-gray-500'>{helperText}</p>}
          <p className='text-xs text-gray-500'>
            {allowedExtensions.join(', ').toUpperCase()} up to {Math.round(maxSize / 1024 / 1024)}MB
          </p>
        </div>
      </div>

      {selectedFile && (
        <div className='mt-2 p-2 bg-gray-50 rounded-md'>
          <p className='text-sm text-gray-700'>
            Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024)}KB)
          </p>
        </div>
      )}

      {/* Validation messages */}
      {validationResult && (
        <div className='space-y-1'>
          {validationResult.errors.map((error, index) => (
            <p key={index} className='text-sm text-red-600 flex items-center'>
              <AlertCircle className='h-3 w-3 mr-1' />
              {error}
            </p>
          ))}

          {validationResult.warnings.map((warning, index) => (
            <p key={index} className='text-sm text-yellow-600 flex items-center'>
              <AlertCircle className='h-3 w-3 mr-1' />
              {warning}
            </p>
          ))}
        </div>
      )}
    </div>
  );
};
