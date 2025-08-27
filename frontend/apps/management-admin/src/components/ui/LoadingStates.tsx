import React from 'react';
import { LoadingSpinner } from './LoadingSpinner';

// Page Loading State
interface PageLoadingProps {
  message?: string;
}

export function PageLoading({ message = 'Loading...' }: PageLoadingProps) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center">
      <LoadingSpinner size="large" />
      <p className="mt-4 text-sm text-gray-600">{message}</p>
    </div>
  );
}

// Card Loading State
interface CardLoadingProps {
  height?: string;
  lines?: number;
}

export function CardLoading({ height = 'h-48', lines = 3 }: CardLoadingProps) {
  return (
    <div className={`card ${height}`}>
      <div className="card-content animate-pulse">
        <div className="space-y-3">
          {Array.from({ length: lines }, (_, i) => (
            <div
              key={i}
              className={`h-4 bg-gray-300 rounded ${
                i === lines - 1 ? 'w-3/4' : 'w-full'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// Table Loading State
interface TableLoadingProps {
  columns: number;
  rows?: number;
}

export function TableLoading({ columns, rows = 5 }: TableLoadingProps) {
  return (
    <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
      <div className="min-w-full divide-y divide-gray-300">
        {/* Header skeleton */}
        <div className="bg-gray-50">
          <div className="grid gap-4 px-6 py-3" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
            {Array.from({ length: columns }, (_, i) => (
              <div key={i} className="h-5 bg-gray-300 rounded animate-pulse" />
            ))}
          </div>
        </div>
        
        {/* Rows skeleton */}
        <div className="bg-white divide-y divide-gray-200">
          {Array.from({ length: rows }, (_, rowIndex) => (
            <div key={rowIndex} className="grid gap-4 px-6 py-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
              {Array.from({ length: columns }, (_, colIndex) => (
                <div 
                  key={colIndex} 
                  className={`h-4 bg-gray-200 rounded animate-pulse ${
                    colIndex === columns - 1 ? 'w-3/4' : 'w-full'
                  }`} 
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// List Loading State
interface ListLoadingProps {
  items?: number;
  showAvatar?: boolean;
}

export function ListLoading({ items = 3, showAvatar = false }: ListLoadingProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }, (_, i) => (
        <div key={i} className="flex items-center space-x-3 p-3 bg-white rounded-lg shadow-sm animate-pulse">
          {showAvatar && (
            <div className="h-10 w-10 bg-gray-300 rounded-full" />
          )}
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-gray-300 rounded w-3/4" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

// Form Loading State
export function FormLoading() {
  return (
    <div className="card">
      <div className="card-content space-y-6 animate-pulse">
        {/* Form fields */}
        <div className="space-y-4">
          <div>
            <div className="h-4 bg-gray-300 rounded w-24 mb-2" />
            <div className="h-10 bg-gray-200 rounded w-full" />
          </div>
          <div>
            <div className="h-4 bg-gray-300 rounded w-32 mb-2" />
            <div className="h-10 bg-gray-200 rounded w-full" />
          </div>
          <div>
            <div className="h-4 bg-gray-300 rounded w-28 mb-2" />
            <div className="h-24 bg-gray-200 rounded w-full" />
          </div>
        </div>
        
        {/* Action buttons */}
        <div className="flex justify-end space-x-3 pt-4 border-t">
          <div className="h-10 bg-gray-300 rounded w-20" />
          <div className="h-10 bg-gray-400 rounded w-24" />
        </div>
      </div>
    </div>
  );
}

// Stats Loading State
interface StatsLoadingProps {
  cards?: number;
}

export function StatsLoading({ cards = 4 }: StatsLoadingProps) {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: cards }, (_, i) => (
        <div key={i} className="card p-5 animate-pulse">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="h-8 w-8 bg-gray-300 rounded" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <div className="h-6 bg-gray-300 rounded w-16 mb-2" />
              <div className="h-4 bg-gray-200 rounded w-24" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Button Loading State
interface ButtonLoadingProps {
  children: React.ReactNode;
  loading: boolean;
  disabled?: boolean;
  className?: string;
  size?: 'small' | 'medium' | 'large';
}

export function ButtonLoading({ 
  children, 
  loading, 
  disabled = false, 
  className = '', 
  size = 'medium' 
}: ButtonLoadingProps) {
  const sizeMap = {
    small: 'small',
    medium: 'small',
    large: 'medium'
  } as const;

  return (
    <button 
      disabled={loading || disabled}
      className={`relative ${className} ${loading ? 'cursor-not-allowed' : ''}`}
    >
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <LoadingSpinner size={sizeMap[size]} color="white" />
        </div>
      )}
      <span className={loading ? 'opacity-0' : 'opacity-100'}>
        {children}
      </span>
    </button>
  );
}

// Content Loading Wrapper
interface ContentLoadingProps {
  loading: boolean;
  error?: string | null;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onRetry?: () => void;
}

export function ContentLoading({ 
  loading, 
  error, 
  children, 
  fallback,
  onRetry 
}: ContentLoadingProps) {
  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-danger-600 mb-4">
          <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.232 18.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Something went wrong</h3>
        <p className="text-sm text-gray-600 mb-4">{error}</p>
        {onRetry && (
          <button 
            onClick={onRetry}
            className="btn-primary"
          >
            Try Again
          </button>
        )}
      </div>
    );
  }

  if (loading) {
    return fallback || <PageLoading />;
  }

  return <>{children}</>;
}