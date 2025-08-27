/**
 * Loading State Components
 * Reusable loading indicators and skeleton loaders
 */

'use client';

import { type ReactNode } from 'react';
import { useLoading } from '../../stores/appStore';

// Basic loading spinner
export function LoadingSpinner({ 
  size = 'medium', 
  className = '' 
}: { 
  size?: 'small' | 'medium' | 'large'; 
  className?: string;
}) {
  const sizeClasses = {
    small: 'w-4 h-4',
    medium: 'w-8 h-8',
    large: 'w-12 h-12',
  };

  return (
    <div
      className={`animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 ${sizeClasses[size]} ${className}`}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}

// Loading overlay for entire sections
export function LoadingOverlay({ 
  isLoading, 
  children, 
  message = 'Loading...',
  className = '' 
}: {
  isLoading: boolean;
  children: ReactNode;
  message?: string;
  className?: string;
}) {
  return (
    <div className={`relative ${className}`}>
      {children}
      {isLoading && (
        <div className="absolute inset-0 bg-white/75 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="flex flex-col items-center space-y-3">
            <LoadingSpinner size="large" />
            <p className="text-sm text-gray-600 font-medium">{message}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// Skeleton loaders for different content types
export function SkeletonLine({ 
  width = 'full',
  height = 'h-4',
  className = ''
}: {
  width?: string;
  height?: string;
  className?: string;
}) {
  const widthClass = width === 'full' ? 'w-full' : width;
  
  return (
    <div
      className={`bg-gray-200 rounded animate-pulse ${widthClass} ${height} ${className}`}
      role="status"
      aria-label="Loading content"
    />
  );
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`border border-gray-200 rounded-lg p-6 space-y-4 ${className}`}>
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 bg-gray-200 rounded-full animate-pulse" />
        <div className="space-y-2 flex-1">
          <SkeletonLine width="w-1/3" height="h-4" />
          <SkeletonLine width="w-1/2" height="h-3" />
        </div>
      </div>
      <div className="space-y-2">
        <SkeletonLine height="h-4" />
        <SkeletonLine width="w-3/4" height="h-4" />
      </div>
    </div>
  );
}

export function SkeletonTable({ 
  rows = 5, 
  columns = 4,
  className = ''
}: { 
  rows?: number; 
  columns?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }).map((_, index) => (
          <SkeletonLine key={`header-${index}`} width="w-3/4" height="h-4" />
        ))}
      </div>
      
      {/* Separator */}
      <div className="border-t border-gray-200" />
      
      {/* Rows */}
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div 
            key={`row-${rowIndex}`}
            className="grid gap-4" 
            style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
          >
            {Array.from({ length: columns }).map((_, colIndex) => (
              <SkeletonLine 
                key={`cell-${rowIndex}-${colIndex}`} 
                width={colIndex === 0 ? 'w-full' : 'w-2/3'} 
                height="h-4" 
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// Loading wrapper that uses global loading state
export function LoadingWrapper({ 
  loadingKey,
  children,
  fallback,
  className = ''
}: {
  loadingKey: string;
  children: ReactNode;
  fallback?: ReactNode;
  className?: string;
}) {
  const { isLoading } = useLoading();
  const loading = isLoading(loadingKey);

  if (loading) {
    return (
      <div className={className}>
        {fallback || <LoadingSpinner />}
      </div>
    );
  }

  return <>{children}</>;
}

// Button with loading state
export function LoadingButton({
  isLoading,
  disabled,
  children,
  loadingText = 'Loading...',
  className = '',
  ...props
}: {
  isLoading?: boolean;
  disabled?: boolean;
  children: ReactNode;
  loadingText?: string;
  className?: string;
  [key: string]: any;
}) {
  const isDisabled = disabled || isLoading;
  
  return (
    <button
      disabled={isDisabled}
      className={`
        relative inline-flex items-center justify-center px-4 py-2 rounded-md
        font-medium text-sm transition-colors
        ${isDisabled 
          ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
          : 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500'
        }
        ${className}
      `}
      {...props}
    >
      {isLoading && (
        <LoadingSpinner size="small" className="mr-2" />
      )}
      {isLoading ? loadingText : children}
    </button>
  );
}

// Generic data loader with error and empty states
export function DataLoader<T>({
  data,
  isLoading,
  error,
  isEmpty,
  children,
  loadingFallback,
  errorFallback,
  emptyFallback,
  className = ''
}: {
  data: T;
  isLoading: boolean;
  error: Error | null;
  isEmpty?: boolean;
  children: (data: T) => ReactNode;
  loadingFallback?: ReactNode;
  errorFallback?: (error: Error) => ReactNode;
  emptyFallback?: ReactNode;
  className?: string;
}) {
  if (isLoading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        {loadingFallback || <LoadingSpinner />}
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-8 ${className}`}>
        {errorFallback ? errorFallback(error) : (
          <div className="text-center">
            <div className="text-red-600 mb-2">⚠️ Error loading data</div>
            <p className="text-sm text-gray-600">{error.message}</p>
          </div>
        )}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className={`p-8 text-center ${className}`}>
        {emptyFallback || (
          <div>
            <div className="text-gray-400 mb-2">📄 No data available</div>
            <p className="text-sm text-gray-500">There's nothing to display yet.</p>
          </div>
        )}
      </div>
    );
  }

  return <>{children(data)}</>;
}

// Progress bar component
export function ProgressBar({
  progress,
  className = '',
  showLabel = true,
  label
}: {
  progress: number;
  className?: string;
  showLabel?: boolean;
  label?: string;
}) {
  const clampedProgress = Math.min(Math.max(progress, 0), 100);
  
  return (
    <div className={`space-y-1 ${className}`}>
      {showLabel && (
        <div className="flex justify-between text-sm">
          <span>{label || 'Progress'}</span>
          <span>{Math.round(clampedProgress)}%</span>
        </div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-in-out"
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
    </div>
  );
}