import React from 'react';
import { clsx } from 'clsx';

export interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  variant?: 'primary' | 'secondary' | 'white';
  text?: string;
  className?: string;
  fullScreen?: boolean;
  overlay?: boolean;
}

export function LoadingSpinner({
  size = 'medium',
  variant = 'primary',
  text,
  className,
  fullScreen = false,
  overlay = false,
}: LoadingSpinnerProps) {
  const sizeClasses = {
    small: 'w-4 h-4',
    medium: 'w-8 h-8',
    large: 'w-12 h-12',
  };

  const variantClasses = {
    primary: 'text-blue-600',
    secondary: 'text-gray-400',
    white: 'text-white',
  };

  const spinnerElement = (
    <div className="flex items-center justify-center">
      <div className="flex flex-col items-center space-y-3">
        <svg
          className={clsx(
            'animate-spin',
            sizeClasses[size],
            variantClasses[variant],
            className
          )}
          fill="none"
          viewBox="0 0 24 24"
          data-testid="loading-spinner"
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
        {text && (
          <p className={clsx(
            'text-sm font-medium',
            variantClasses[variant] === 'text-white'
              ? 'text-white'
              : 'text-gray-600'
          )}>
            {text}
          </p>
        )}
      </div>
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-white">
        {spinnerElement}
      </div>
    );
  }

  if (overlay) {
    return (
      <div className="absolute inset-0 z-40 flex items-center justify-center bg-white bg-opacity-75 backdrop-blur-sm">
        {spinnerElement}
      </div>
    );
  }

  return spinnerElement;
}

// Loading states for different contexts
export function PageLoading({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <LoadingSpinner size="large" text={message} />
    </div>
  );
}

export function CardLoading({ message }: { message?: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <LoadingSpinner size="medium" text={message} />
    </div>
  );
}

export function ButtonLoading({ size = 'small' }: { size?: LoadingSpinnerProps['size'] }) {
  return <LoadingSpinner size={size} variant="white" />;
}

export function TableLoading({ rows = 5 }: { rows?: number }) {
  return (
    <div className="animate-pulse">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="border-b border-gray-200 px-6 py-4">
          <div className="flex space-x-4">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/6"></div>
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/6"></div>
            <div className="h-4 bg-gray-200 rounded w-1/8"></div>
          </div>
        </div>
      ))}
    </div>
  );
}
