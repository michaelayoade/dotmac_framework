import React, { forwardRef } from 'react';
import { LoadingSpinner } from './LoadingSpinner';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline' | 'ghost';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  leftIcon?: React.ComponentType<{ className?: string }>;
  rightIcon?: React.ComponentType<{ className?: string }>;
  fullWidth?: boolean;
}

const variantStyles = {
  primary: 'btn-primary',
  secondary: 'btn-secondary', 
  danger: 'btn-danger',
  success: 'btn-success',
  outline: 'border-2 border-gray-300 text-gray-700 bg-transparent hover:bg-gray-50 focus:ring-2 focus:ring-primary-500',
  ghost: 'text-gray-700 bg-transparent hover:bg-gray-100 focus:ring-2 focus:ring-primary-500',
};

const sizeStyles = {
  xs: 'px-2 py-1 text-xs',
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm', // default
  lg: 'px-6 py-3 text-base',
  xl: 'px-8 py-4 text-lg',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    children,
    variant = 'primary',
    size = 'md',
    loading = false,
    leftIcon: LeftIcon,
    rightIcon: RightIcon,
    fullWidth = false,
    disabled,
    className = '',
    type = 'button',
    ...props 
  }, ref) => {
    const isDisabled = disabled || loading;

    const classes = `
      ${variantStyles[variant]}
      ${sizeStyles[size]}
      ${fullWidth ? 'w-full' : ''}
      ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}
      inline-flex items-center justify-center
      font-medium rounded-md transition-colors duration-200
      focus:outline-none focus:ring-2 focus:ring-offset-2
      touch-manipulation tap-highlight-transparent
      ${className}
    `;

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={classes}
        {...props}
      >
        {loading && (
          <LoadingSpinner 
            size="small" 
            color={variant === 'primary' || variant === 'danger' || variant === 'success' ? 'white' : 'primary'}
            className="mr-2"
          />
        )}
        
        {!loading && LeftIcon && (
          <LeftIcon className="mr-2 h-4 w-4" />
        )}
        
        <span className={loading ? 'opacity-0' : 'opacity-100'}>
          {children}
        </span>
        
        {!loading && RightIcon && (
          <RightIcon className="ml-2 h-4 w-4" />
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

// Icon Button Component
interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ComponentType<{ className?: string }>;
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline' | 'ghost';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  'aria-label': string;
}

const iconSizeStyles = {
  xs: 'p-1',
  sm: 'p-1.5', 
  md: 'p-2',
  lg: 'p-3',
  xl: 'p-4',
};

const iconStyles = {
  xs: 'h-3 w-3',
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-6 w-6', 
  xl: 'h-8 w-8',
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({
    icon: Icon,
    variant = 'ghost',
    size = 'md',
    loading = false,
    disabled,
    className = '',
    ...props
  }, ref) => {
    const isDisabled = disabled || loading;

    const classes = `
      ${variantStyles[variant]}
      ${iconSizeStyles[size]}
      ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}
      inline-flex items-center justify-center
      rounded-full transition-colors duration-200
      focus:outline-none focus:ring-2 focus:ring-offset-2
      touch-manipulation tap-highlight-transparent
      ${className}
    `;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={classes}
        {...props}
      >
        {loading ? (
          <LoadingSpinner 
            size="small"
            color={variant === 'primary' || variant === 'danger' || variant === 'success' ? 'white' : 'primary'}
          />
        ) : (
          <Icon className={iconStyles[size]} />
        )}
      </button>
    );
  }
);

IconButton.displayName = 'IconButton';

// Button Group Component
interface ButtonGroupProps {
  children: React.ReactNode;
  orientation?: 'horizontal' | 'vertical';
  spacing?: 'none' | 'sm' | 'md' | 'lg';
  className?: string;
}

export function ButtonGroup({ 
  children, 
  orientation = 'horizontal', 
  spacing = 'sm',
  className = '' 
}: ButtonGroupProps) {
  const orientationClasses = {
    horizontal: 'flex-row',
    vertical: 'flex-col',
  };

  const spacingClasses = {
    none: orientation === 'horizontal' ? 'space-x-0' : 'space-y-0',
    sm: orientation === 'horizontal' ? 'space-x-2' : 'space-y-2',
    md: orientation === 'horizontal' ? 'space-x-3' : 'space-y-3',
    lg: orientation === 'horizontal' ? 'space-x-4' : 'space-y-4',
  };

  return (
    <div className={`
      flex ${orientationClasses[orientation]} ${spacingClasses[spacing]} ${className}
    `}>
      {children}
    </div>
  );
}