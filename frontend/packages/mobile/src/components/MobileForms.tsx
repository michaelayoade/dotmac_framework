/**
 * Mobile-Optimized Form Components
 * Touch-friendly inputs and form controls
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { clsx } from 'clsx';
import { useVibration } from '../hardware/useDevice';

export interface MobileInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  success?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  clearable?: boolean;
  haptic?: boolean;
  autoHeight?: boolean;
  variant?: 'default' | 'rounded' | 'minimal';
}

export function MobileInput({
  label,
  error,
  success,
  leftIcon,
  rightIcon,
  clearable = false,
  haptic = true,
  autoHeight = false,
  variant = 'default',
  className,
  value,
  onChange,
  onFocus,
  onBlur,
  ...props
}: MobileInputProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [hasValue, setHasValue] = useState(Boolean(value));
  const inputRef = useRef<HTMLInputElement>(null);
  const { vibrate } = useVibration();

  const triggerHaptic = useCallback(() => {
    if (haptic) {
      vibrate(10);
    }
  }, [haptic, vibrate]);

  const handleFocus = useCallback((event: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(true);
    triggerHaptic();
    onFocus?.(event);
  }, [onFocus, triggerHaptic]);

  const handleBlur = useCallback((event: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(false);
    onBlur?.(event);
  }, [onBlur]);

  const handleChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    setHasValue(Boolean(newValue));
    onChange?.(event);
  }, [onChange]);

  const handleClear = useCallback(() => {
    if (inputRef.current) {
      const event = new Event('input', { bubbles: true });
      inputRef.current.value = '';
      inputRef.current.dispatchEvent(event);
      setHasValue(false);
      triggerHaptic();
      inputRef.current.focus();
    }
  }, [triggerHaptic]);

  useEffect(() => {
    setHasValue(Boolean(value));
  }, [value]);

  const getVariantClasses = () => {
    switch (variant) {
      case 'rounded':
        return 'rounded-full border-2';
      case 'minimal':
        return 'border-0 border-b-2 rounded-none bg-transparent';
      default:
        return 'rounded-lg border';
    }
  };

  return (
    <div className={clsx('mobile-input-container', 'w-full', className)}>
      {/* Label */}
      {label && (
        <label
          className={clsx(
            'block text-sm font-medium mb-2 transition-colors duration-200',
            error ? 'text-red-600' : success ? 'text-green-600' : 'text-gray-700'
          )}
          htmlFor={props.id}
        >
          {label}
        </label>
      )}

      {/* Input Container */}
      <div className="relative">
        {/* Left Icon */}
        {leftIcon && (
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none">
            {leftIcon}
          </div>
        )}

        {/* Input */}
        <input
          ref={inputRef}
          className={clsx(
            'w-full transition-all duration-200 touch-manipulation',
            'min-h-[48px] px-4 py-3 text-base',
            'placeholder-gray-400 focus:outline-none',
            getVariantClasses(),
            {
              // Border states
              'border-red-500 focus:border-red-600 focus:ring-2 focus:ring-red-100': error,
              'border-green-500 focus:border-green-600 focus:ring-2 focus:ring-green-100': success && !error,
              'border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100': !error && !success,
              
              // Background states
              'bg-white': variant !== 'minimal',
              'bg-gray-50': isFocused && variant !== 'minimal',
              
              // Padding adjustments for icons
              'pl-10': leftIcon,
              'pr-10': rightIcon || clearable,
              'pr-16': rightIcon && clearable,
              
              // Auto height for textareas
              'min-h-[120px] resize-y': autoHeight && props.type === undefined,
              
              // Disabled state
              'opacity-50 cursor-not-allowed': props.disabled
            }
          )}
          value={value}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          {...props}
        />

        {/* Right Icons */}
        <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center space-x-2">
          {/* Clear Button */}
          {clearable && hasValue && !props.disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="text-gray-400 hover:text-gray-600 touch-manipulation p-1"
              aria-label="Clear input"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}

          {/* Right Icon */}
          {rightIcon && (
            <div className="text-gray-400 pointer-events-none">
              {rightIcon}
            </div>
          )}
        </div>

        {/* Floating Label */}
        {variant === 'minimal' && label && (
          <label
            className={clsx(
              'absolute left-0 transition-all duration-200 pointer-events-none',
              {
                'top-1/2 transform -translate-y-1/2 text-base text-gray-400': !isFocused && !hasValue,
                'top-0 text-xs text-blue-600 font-medium': isFocused || hasValue
              }
            )}
            htmlFor={props.id}
          >
            {label}
          </label>
        )}
      </div>

      {/* Error/Success Message */}
      {(error || success) && (
        <div className={clsx(
          'mt-2 text-sm flex items-center space-x-1',
          error ? 'text-red-600' : 'text-green-600'
        )}>
          {/* Icon */}
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {error ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            )}
          </svg>
          
          {/* Message */}
          <span>{error || (success ? 'Valid' : '')}</span>
        </div>
      )}
    </div>
  );
}

// Mobile Select Component
export interface MobileSelectProps {
  label?: string;
  placeholder?: string;
  options: { value: string; label: string; disabled?: boolean }[];
  value?: string;
  onChange?: (value: string) => void;
  error?: string;
  disabled?: boolean;
  haptic?: boolean;
  className?: string;
}

export function MobileSelect({
  label,
  placeholder = 'Select an option',
  options,
  value,
  onChange,
  error,
  disabled = false,
  haptic = true,
  className
}: MobileSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { vibrate } = useVibration();

  const triggerHaptic = useCallback(() => {
    if (haptic) {
      vibrate(10);
    }
  }, [haptic, vibrate]);

  const handleToggle = useCallback(() => {
    if (disabled) return;
    setIsOpen(!isOpen);
    triggerHaptic();
  }, [disabled, isOpen, triggerHaptic]);

  const handleSelect = useCallback((optionValue: string) => {
    onChange?.(optionValue);
    setIsOpen(false);
    triggerHaptic();
  }, [onChange, triggerHaptic]);

  const selectedOption = options.find(opt => opt.value === value);

  return (
    <div className={clsx('mobile-select-container', 'relative', className)}>
      {/* Label */}
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
      )}

      {/* Select Button */}
      <button
        type="button"
        onClick={handleToggle}
        disabled={disabled}
        className={clsx(
          'w-full min-h-[48px] px-4 py-3 text-left bg-white border rounded-lg',
          'flex items-center justify-between touch-manipulation',
          'transition-all duration-200 focus:outline-none focus:ring-2',
          {
            'border-red-500 focus:border-red-600 focus:ring-red-100': error,
            'border-gray-300 focus:border-blue-500 focus:ring-blue-100': !error,
            'opacity-50 cursor-not-allowed': disabled,
            'hover:border-gray-400': !disabled && !error
          }
        )}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className={clsx(
          'text-base',
          selectedOption ? 'text-gray-900' : 'text-gray-400'
        )}>
          {selectedOption?.label || placeholder}
        </span>

        <svg
          className={clsx(
            'w-5 h-5 text-gray-400 transition-transform duration-200',
            { 'transform rotate-180': isOpen }
          )}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Options List */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Options */}
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-60 overflow-auto">
            {options.map((option) => (
              <button
                key={option.value}
                onClick={() => handleSelect(option.value)}
                disabled={option.disabled}
                className={clsx(
                  'w-full px-4 py-3 text-left text-base transition-colors duration-150',
                  'hover:bg-gray-50 active:bg-gray-100 touch-manipulation',
                  'first:rounded-t-lg last:rounded-b-lg',
                  {
                    'bg-blue-50 text-blue-600 font-medium': option.value === value,
                    'text-gray-900': option.value !== value && !option.disabled,
                    'text-gray-400 cursor-not-allowed': option.disabled
                  }
                )}
                role="option"
                aria-selected={option.value === value}
              >
                {option.label}
                
                {/* Selected indicator */}
                {option.value === value && (
                  <svg className="w-4 h-4 inline ml-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </>
      )}

      {/* Error Message */}
      {error && (
        <div className="mt-2 text-sm text-red-600 flex items-center space-x-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

// Mobile Checkbox
export interface MobileCheckboxProps {
  label?: string;
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  haptic?: boolean;
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

export function MobileCheckbox({
  label,
  checked = false,
  onChange,
  disabled = false,
  haptic = true,
  size = 'medium',
  className
}: MobileCheckboxProps) {
  const { vibrate } = useVibration();

  const handleChange = useCallback(() => {
    if (disabled) return;
    
    if (haptic) {
      vibrate(checked ? [10] : [15]);
    }
    
    onChange?.(!checked);
  }, [disabled, checked, onChange, haptic, vibrate]);

  const sizeClasses = {
    small: 'w-5 h-5',
    medium: 'w-6 h-6',
    large: 'w-7 h-7'
  };

  return (
    <label className={clsx(
      'mobile-checkbox flex items-center space-x-3 cursor-pointer touch-manipulation',
      'select-none transition-opacity duration-200',
      {
        'opacity-50 cursor-not-allowed': disabled
      },
      className
    )}>
      {/* Checkbox */}
      <div className="relative flex-shrink-0">
        <input
          type="checkbox"
          checked={checked}
          onChange={handleChange}
          disabled={disabled}
          className="sr-only"
        />
        
        <div className={clsx(
          'border-2 rounded-md transition-all duration-200 flex items-center justify-center',
          sizeClasses[size],
          {
            'border-blue-500 bg-blue-500': checked && !disabled,
            'border-gray-300 bg-white': !checked && !disabled,
            'border-gray-200 bg-gray-100': disabled,
            'hover:border-blue-400': !disabled && !checked,
            'hover:bg-blue-600': !disabled && checked
          }
        )}>
          {/* Checkmark */}
          {checked && (
            <svg
              className="text-white w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M5 13l4 4L19 7"
              />
            </svg>
          )}
        </div>

        {/* Focus Ring */}
        <div className={clsx(
          'absolute inset-0 rounded-md ring-2 ring-blue-500 ring-opacity-0',
          'transition-all duration-200 pointer-events-none',
          {
            'ring-opacity-100': checked && !disabled
          }
        )} />
      </div>

      {/* Label */}
      {label && (
        <span className={clsx(
          'text-base flex-1',
          disabled ? 'text-gray-400' : 'text-gray-900'
        )}>
          {label}
        </span>
      )}
    </label>
  );
}

// Mobile Switch
export interface MobileSwitchProps {
  label?: string;
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  haptic?: boolean;
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

export function MobileSwitch({
  label,
  checked = false,
  onChange,
  disabled = false,
  haptic = true,
  size = 'medium',
  className
}: MobileSwitchProps) {
  const { vibrate } = useVibration();

  const handleToggle = useCallback(() => {
    if (disabled) return;
    
    if (haptic) {
      vibrate(checked ? [10] : [15]);
    }
    
    onChange?.(!checked);
  }, [disabled, checked, onChange, haptic, vibrate]);

  const sizeClasses = {
    small: { container: 'w-10 h-6', thumb: 'w-4 h-4' },
    medium: { container: 'w-12 h-7', thumb: 'w-5 h-5' },
    large: { container: 'w-14 h-8', thumb: 'w-6 h-6' }
  };

  const sizes = sizeClasses[size];

  return (
    <label className={clsx(
      'mobile-switch flex items-center justify-between cursor-pointer touch-manipulation',
      'select-none transition-opacity duration-200',
      {
        'opacity-50 cursor-not-allowed': disabled
      },
      className
    )}>
      {/* Label */}
      {label && (
        <span className={clsx(
          'text-base mr-3',
          disabled ? 'text-gray-400' : 'text-gray-900'
        )}>
          {label}
        </span>
      )}

      {/* Switch */}
      <div className="relative flex-shrink-0">
        <input
          type="checkbox"
          checked={checked}
          onChange={handleToggle}
          disabled={disabled}
          className="sr-only"
        />
        
        {/* Track */}
        <div className={clsx(
          'rounded-full transition-all duration-200 border-2',
          sizes.container,
          {
            'bg-blue-500 border-blue-500': checked && !disabled,
            'bg-gray-200 border-gray-200': !checked && !disabled,
            'bg-gray-100 border-gray-100': disabled
          }
        )} />

        {/* Thumb */}
        <div className={clsx(
          'absolute top-0.5 bg-white rounded-full shadow-sm transition-transform duration-200',
          sizes.thumb,
          {
            'transform translate-x-full': checked,
            'transform translate-x-0.5': !checked
          }
        )} />

        {/* Focus Ring */}
        <div className={clsx(
          'absolute inset-0 rounded-full ring-2 ring-blue-500 ring-opacity-0',
          'transition-all duration-200 pointer-events-none',
          {
            'ring-opacity-100': checked && !disabled
          }
        )} />
      </div>
    </label>
  );
}

// Enhanced styles
export const MobileFormStyles = `
  .mobile-input-container {
    /* Touch optimization */
    -webkit-tap-highlight-color: transparent;
  }

  .mobile-input-container input {
    /* Prevent zoom on iOS */
    font-size: 16px;
    
    /* Better touch scrolling */
    -webkit-overflow-scrolling: touch;
    
    /* Optimize for performance */
    transform: translateZ(0);
  }

  /* Safe area support */
  @supports (padding-left: env(safe-area-inset-left)) {
    .mobile-input-container {
      padding-left: env(safe-area-inset-left);
      padding-right: env(safe-area-inset-right);
    }
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    .mobile-input-container *,
    .mobile-checkbox *,
    .mobile-switch * {
      transition: none;
    }
  }

  /* High contrast mode */
  @media (prefers-contrast: high) {
    .mobile-input-container input,
    .mobile-checkbox div,
    .mobile-switch div {
      border-width: 2px;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .mobile-input-container input {
      background-color: #374151;
      border-color: #4b5563;
      color: #f9fafb;
    }
    
    .mobile-input-container input::placeholder {
      color: #9ca3af;
    }
  }
`;