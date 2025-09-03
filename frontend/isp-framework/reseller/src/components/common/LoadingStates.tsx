/**
 * Comprehensive Loading State Components
 * Provides consistent loading indicators across the application
 */

import { Loader2, RefreshCw } from 'lucide-react';
import type React from 'react';

// Basic loading spinner
export function LoadingSpinner({
  size = 'md',
  className = '',
}: {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  };

  return (
    <Loader2 className={`animate-spin ${sizeClasses[size]} ${className}`} aria-label='Loading' />
  );
}

// Page-level loading screen
export function PageLoading({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className='min-h-[60vh] flex items-center justify-center'>
      <div className='text-center'>
        <LoadingSpinner size='lg' className='text-green-600 mb-4 mx-auto' />
        <p className='text-gray-600 font-medium'>{message}</p>
        <p className='text-sm text-gray-500 mt-2'>Please wait while we load your data</p>
      </div>
    </div>
  );
}

// Section-level loading state
export function SectionLoading({
  message = 'Loading section...',
  height = 'h-32',
}: {
  message?: string;
  height?: string;
}) {
  return (
    <div
      className={`${height} flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200`}
    >
      <div className='text-center'>
        <LoadingSpinner className='text-green-600 mb-2 mx-auto' />
        <p className='text-sm text-gray-600'>{message}</p>
      </div>
    </div>
  );
}

// Table loading skeleton
export function TableLoading({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className='animate-pulse'>
      <div className='overflow-hidden bg-white shadow rounded-lg'>
        {/* Header */}
        <div className='bg-gray-50 px-6 py-3 border-b border-gray-200'>
          <div className='flex space-x-4'>
            {Array.from({ length: columns }).map((_, i) => (
              <div key={i} className='h-4 bg-gray-200 rounded flex-1'></div>
            ))}
          </div>
        </div>
        {/* Rows */}
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className='px-6 py-4 border-b border-gray-200'>
            <div className='flex space-x-4'>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <div
                  key={colIndex}
                  className={`h-4 bg-gray-200 rounded flex-1 ${
                    colIndex === 0 ? 'bg-gray-300' : ''
                  }`}
                ></div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Card loading skeleton
export function CardLoading({ count = 1, height = 'h-32' }: { count?: number; height?: string }) {
  return (
    <div className='grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3'>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className='animate-pulse'>
          <div className={`${height} bg-white rounded-lg shadow border border-gray-200 p-6`}>
            <div className='flex items-start justify-between mb-4'>
              <div className='h-4 bg-gray-200 rounded w-1/3'></div>
              <div className='h-8 w-8 bg-gray-200 rounded'></div>
            </div>
            <div className='space-y-3'>
              <div className='h-6 bg-gray-300 rounded w-1/2'></div>
              <div className='h-4 bg-gray-200 rounded w-3/4'></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Chart loading placeholder
export function ChartLoading({
  height = 'h-80',
  title = 'Loading chart...',
}: {
  height?: string;
  title?: string;
}) {
  return (
    <div className={`${height} bg-white rounded-lg shadow border border-gray-200 p-6`}>
      <div className='animate-pulse'>
        <div className='h-6 bg-gray-200 rounded w-1/4 mb-6'></div>
        <div className='space-y-3 h-full'>
          <div className='h-4 bg-gray-200 rounded w-full'></div>
          <div className='h-4 bg-gray-200 rounded w-5/6'></div>
          <div className='h-4 bg-gray-200 rounded w-4/6'></div>
          <div className='h-4 bg-gray-200 rounded w-3/6'></div>
          <div className='h-4 bg-gray-200 rounded w-2/6'></div>
        </div>
        <div className='flex justify-center items-center h-24 mt-4'>
          <div className='text-gray-400 text-sm'>{title}</div>
        </div>
      </div>
    </div>
  );
}

// Button loading state
export function ButtonLoading({
  children,
  isLoading = false,
  className = '',
  ...props
}: {
  children: React.ReactNode;
  isLoading?: boolean;
  className?: string;
  [key: string]: any;
}) {
  return (
    <button
      className={`relative ${className} ${isLoading ? 'cursor-not-allowed opacity-75' : ''}`}
      disabled={isLoading}
      {...props}
    >
      {isLoading && (
        <div className='absolute inset-0 flex items-center justify-center'>
          <LoadingSpinner size='sm' className='text-current' />
        </div>
      )}
      <span className={isLoading ? 'invisible' : 'visible'}>{children}</span>
    </button>
  );
}

// Form loading state
export function FormLoading() {
  return (
    <div className='animate-pulse space-y-6'>
      <div>
        <div className='h-4 bg-gray-200 rounded w-1/4 mb-2'></div>
        <div className='h-10 bg-gray-200 rounded w-full'></div>
      </div>
      <div>
        <div className='h-4 bg-gray-200 rounded w-1/3 mb-2'></div>
        <div className='h-10 bg-gray-200 rounded w-full'></div>
      </div>
      <div>
        <div className='h-4 bg-gray-200 rounded w-1/4 mb-2'></div>
        <div className='h-20 bg-gray-200 rounded w-full'></div>
      </div>
      <div className='flex space-x-4'>
        <div className='h-10 bg-gray-300 rounded w-24'></div>
        <div className='h-10 bg-gray-200 rounded w-20'></div>
      </div>
    </div>
  );
}

// Inline loading with message
export function InlineLoading({
  message = 'Loading...',
  showSpinner = true,
}: {
  message?: string;
  showSpinner?: boolean;
}) {
  return (
    <div className='flex items-center justify-center py-4'>
      {showSpinner && <LoadingSpinner size='sm' className='text-green-600 mr-2' />}
      <span className='text-gray-600 text-sm'>{message}</span>
    </div>
  );
}

// Refresh loading state
export function RefreshLoading({
  isRefreshing = false,
  onRefresh,
  children,
  className = '',
}: {
  isRefreshing?: boolean;
  onRefresh?: () => void;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`relative ${className}`}>
      {isRefreshing && (
        <div className='absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center z-10 rounded'>
          <div className='text-center'>
            <RefreshCw className='h-6 w-6 animate-spin text-green-600 mx-auto mb-2' />
            <p className='text-sm text-gray-600'>Refreshing...</p>
          </div>
        </div>
      )}
      <div className={isRefreshing ? 'opacity-50 pointer-events-none' : ''}>{children}</div>
    </div>
  );
}
