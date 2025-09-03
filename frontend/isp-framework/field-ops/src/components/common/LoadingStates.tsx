'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Loader2, Wifi, WifiOff } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
}

export function LoadingSpinner({ size = 'md', text, className = '' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <div className={`flex items-center justify-center space-x-2 ${className}`}>
      <Loader2 className={`animate-spin ${sizeClasses[size]}`} />
      {text && <span className='text-sm text-gray-600'>{text}</span>}
    </div>
  );
}

interface SkeletonProps {
  className?: string;
  animate?: boolean;
}

export function Skeleton({ className = '', animate = true }: SkeletonProps) {
  const baseClasses = 'bg-gray-200 rounded';
  const animationClasses = animate ? 'animate-pulse' : '';

  return <div className={`${baseClasses} ${animationClasses} ${className}`} />;
}

// Work Order List Skeleton
export function WorkOrderListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className='space-y-4'>
      {/* Search and Filter Skeleton */}
      <div className='mobile-card'>
        <div className='space-y-3'>
          <Skeleton className='h-10 w-full' />
          <Skeleton className='h-10 w-full' />
        </div>
      </div>

      {/* Work Orders Skeleton */}
      <div className='space-y-3'>
        {[...Array(count)].map((_, index) => (
          <div key={index} className='mobile-card'>
            <div className='flex space-x-3'>
              {/* Priority Indicator */}
              <Skeleton className='w-2 h-16' />

              <div className='flex-1 space-y-2'>
                {/* Header */}
                <div className='flex items-start justify-between'>
                  <div className='flex-1 space-y-1'>
                    <Skeleton className='h-4 w-3/4' />
                    <Skeleton className='h-3 w-1/3' />
                  </div>
                  <Skeleton className='h-6 w-20' />
                </div>

                {/* Customer Info */}
                <div className='flex items-center space-x-4'>
                  <Skeleton className='h-4 w-32' />
                  <Skeleton className='h-4 w-16' />
                </div>

                {/* Location */}
                <div className='flex items-start justify-between'>
                  <Skeleton className='h-4 w-48' />
                  <Skeleton className='h-4 w-20' />
                </div>

                {/* Schedule */}
                <div className='flex items-center justify-between'>
                  <Skeleton className='h-4 w-40' />
                  <Skeleton className='h-3 w-24' />
                </div>

                {/* Progress */}
                <div className='space-y-2'>
                  <div className='flex justify-between'>
                    <Skeleton className='h-3 w-16' />
                    <Skeleton className='h-3 w-8' />
                  </div>
                  <Skeleton className='h-1.5 w-full' />
                </div>

                {/* Buttons */}
                <div className='flex space-x-2'>
                  <Skeleton className='h-8 flex-1' />
                  <Skeleton className='h-8 w-24' />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Customer List Skeleton
export function CustomerListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className='space-y-3'>
      {[...Array(count)].map((_, index) => (
        <div key={index} className='mobile-card'>
          <div className='flex items-center space-x-4'>
            <Skeleton className='h-12 w-12 rounded-full' />
            <div className='flex-1 space-y-2'>
              <Skeleton className='h-4 w-3/4' />
              <Skeleton className='h-3 w-1/2' />
              <div className='flex space-x-2'>
                <Skeleton className='h-3 w-16' />
                <Skeleton className='h-3 w-20' />
              </div>
            </div>
            <Skeleton className='h-6 w-16' />
          </div>
        </div>
      ))}
    </div>
  );
}

// Inventory List Skeleton
export function InventoryListSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className='grid grid-cols-2 gap-3'>
      {[...Array(count)].map((_, index) => (
        <div key={index} className='mobile-card p-3'>
          <div className='space-y-2'>
            <Skeleton className='h-4 w-full' />
            <Skeleton className='h-3 w-2/3' />
            <div className='flex justify-between items-center'>
              <Skeleton className='h-3 w-12' />
              <Skeleton className='h-4 w-8' />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Form Loading State
export function FormLoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className='flex flex-col items-center justify-center p-8 space-y-4'>
      <LoadingSpinner size='lg' />
      <p className='text-gray-600 text-center'>{message}</p>
    </div>
  );
}

// Page Loading State
export function PageLoadingState({ message = 'Loading page...' }: { message?: string }) {
  return (
    <div className='min-h-screen flex flex-col items-center justify-center bg-gray-50'>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className='text-center space-y-4'
      >
        <LoadingSpinner size='lg' />
        <h2 className='text-lg font-medium text-gray-900'>{message}</h2>
      </motion.div>
    </div>
  );
}

// Network Status Indicator
export function NetworkStatusIndicator({ isOnline }: { isOnline: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      className={`fixed top-4 left-4 z-50 flex items-center space-x-2 px-3 py-2 rounded-lg shadow-md ${
        isOnline ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      }`}
    >
      {isOnline ? <Wifi className='w-4 h-4' /> : <WifiOff className='w-4 h-4' />}
      <span className='text-sm font-medium'>{isOnline ? 'Online' : 'Offline'}</span>
    </motion.div>
  );
}

// Sync Status Indicator
export function SyncStatusIndicator({
  status,
  pendingCount = 0,
}: {
  status: 'idle' | 'syncing' | 'error';
  pendingCount?: number;
}) {
  if (status === 'idle' && pendingCount === 0) {
    return null;
  }

  return (
    <div className='fixed bottom-4 left-4 z-50'>
      <div className='flex items-center space-x-2 bg-white shadow-lg rounded-lg px-3 py-2 border'>
        {status === 'syncing' && (
          <>
            <LoadingSpinner size='sm' />
            <span className='text-sm text-gray-700'>Syncing changes...</span>
          </>
        )}
        {status === 'error' && (
          <>
            <div className='w-2 h-2 bg-red-500 rounded-full animate-pulse' />
            <span className='text-sm text-red-700'>Sync failed</span>
          </>
        )}
        {status === 'idle' && pendingCount > 0 && (
          <>
            <div className='w-2 h-2 bg-yellow-500 rounded-full animate-pulse' />
            <span className='text-sm text-gray-700'>
              {pendingCount} pending change{pendingCount !== 1 ? 's' : ''}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

// Empty State Component
export function EmptyState({
  title,
  description,
  icon: Icon,
  action,
}: {
  title: string;
  description: string;
  icon?: React.ElementType;
  action?: {
    label: string;
    onClick: () => void;
  };
}) {
  return (
    <div className='text-center py-12'>
      {Icon && <Icon className='w-12 h-12 text-gray-400 mx-auto mb-4' />}
      <h3 className='text-lg font-medium text-gray-900 mb-2'>{title}</h3>
      <p className='text-gray-600 mb-6 max-w-sm mx-auto'>{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className='bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors'
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// Error State Component
export function ErrorState({
  title,
  description,
  onRetry,
}: {
  title: string;
  description: string;
  onRetry?: () => void;
}) {
  return (
    <div className='text-center py-12'>
      <div className='w-12 h-12 text-red-500 mx-auto mb-4'>
        <svg fill='none' stroke='currentColor' viewBox='0 0 24 24'>
          <path
            strokeLinecap='round'
            strokeLinejoin='round'
            strokeWidth={2}
            d='M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
          />
        </svg>
      </div>
      <h3 className='text-lg font-medium text-gray-900 mb-2'>{title}</h3>
      <p className='text-gray-600 mb-6 max-w-sm mx-auto'>{description}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className='bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700 transition-colors'
        >
          Try Again
        </button>
      )}
    </div>
  );
}
