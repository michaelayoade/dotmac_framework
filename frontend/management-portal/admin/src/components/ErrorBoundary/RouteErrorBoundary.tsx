'use client';

import React from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import {
  ExclamationTriangleIcon as AlertTriangleIcon,
  ArrowPathIcon as RefreshCwIcon,
  HomeIcon,
  BugAntIcon,
} from '@heroicons/react/24/outline';
import { useAppNavigation, routes } from '@/lib/navigation';
import { api } from '@/lib/http';

interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  const { push } = useAppNavigation();

  const errorDetails = {
    message: error.message || 'An unexpected error occurred',
    stack: error.stack,
    timestamp: new Date().toISOString(),
    userAgent: typeof window !== 'undefined' ? window.navigator.userAgent : 'Unknown',
  };

  const handleReportError = () => {
    // In a real app, this would send to error tracking service
    console.error('Error reported:', errorDetails);

    // You could integrate with Sentry, LogRocket, etc.
    if (typeof window !== 'undefined') {
      try {
        // Example: Send to monitoring API
        api
          .post('/api/security/events', {
            type: 'error_boundary_triggered',
            error: {
              message: error.message,
              stack: error.stack,
              component: 'RouteErrorBoundary',
            },
            metadata: errorDetails,
          })
          .catch(console.error);
      } catch (reportError) {
        console.error('Failed to report error:', reportError);
      }
    }
  };

  return (
    <div className='min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8'>
      <div className='sm:mx-auto sm:w-full sm:max-w-lg'>
        <div className='bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10'>
          <div className='text-center'>
            <AlertTriangleIcon className='mx-auto h-16 w-16 text-red-500' />
            <h1 className='mt-6 text-3xl font-bold text-gray-900'>Oops! Something went wrong</h1>
            <p className='mt-4 text-base text-gray-600'>
              We encountered an unexpected error. Don't worry, this has been reported to our team
              and we're working to fix it.
            </p>

            {/* Error details for development */}
            {process.env.NODE_ENV === 'development' && (
              <div className='mt-4 p-4 bg-gray-100 rounded-lg text-left'>
                <h3 className='text-sm font-medium text-gray-900 mb-2'>
                  Error Details (Dev Mode):
                </h3>
                <p className='text-xs font-mono text-gray-700 break-all'>{error.message}</p>
                {error.stack && (
                  <details className='mt-2'>
                    <summary className='text-xs text-gray-600 cursor-pointer'>Stack Trace</summary>
                    <pre className='text-xs text-gray-600 mt-2 overflow-auto max-h-40'>
                      {error.stack}
                    </pre>
                  </details>
                )}
              </div>
            )}

            {/* Action buttons */}
            <div className='mt-8 flex flex-col sm:flex-row gap-3'>
              <button
                onClick={resetErrorBoundary}
                className='flex-1 flex justify-center items-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors'
              >
                <RefreshCwIcon className='h-4 w-4 mr-2' />
                Try Again
              </button>

              <button
                onClick={() => push(routes.dashboard)}
                className='flex-1 flex justify-center items-center py-3 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors'
              >
                <HomeIcon className='h-4 w-4 mr-2' />
                Go to Dashboard
              </button>
            </div>

            {/* Report button */}
            <div className='mt-4'>
              <button
                onClick={handleReportError}
                className='inline-flex items-center text-sm text-gray-500 hover:text-gray-700 transition-colors'
              >
                <BugAntIcon className='h-4 w-4 mr-1' />
                Report this issue
              </button>
            </div>

            {/* Help text */}
            <p className='mt-4 text-xs text-gray-500'>
              If this problem persists, please contact our support team with the error details
              above.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

interface RouteErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

export function RouteErrorBoundary({
  children,
  fallback: FallbackComponent = ErrorFallback,
  onError,
}: RouteErrorBoundaryProps) {
  const handleError = (error: Error, errorInfo: React.ErrorInfo) => {
    console.error('Route Error Boundary caught an error:', error, errorInfo);

    // Call custom error handler if provided
    if (onError) {
      onError(error, errorInfo);
    }

    // Send to error tracking service
    if (typeof window !== 'undefined') {
      try {
        api
          .post('/api/security/events', {
            type: 'react_error_boundary',
            error: {
              message: error.message,
              stack: error.stack,
              name: error.name,
            },
            errorInfo: {
              componentStack: errorInfo.componentStack,
            },
            metadata: {
              timestamp: new Date().toISOString(),
              url: window.location.href,
              userAgent: window.navigator.userAgent,
            },
          })
          .catch(console.error);
      } catch (reportError) {
        console.error('Failed to report error to API:', reportError);
      }
    }
  };

  return (
    <ErrorBoundary
      FallbackComponent={FallbackComponent}
      onError={handleError}
      onReset={() => {
        // Clear any error state when resetting
        if (typeof window !== 'undefined') {
          window.location.reload();
        }
      }}
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * HOC for wrapping components with error boundary
 */
export function withErrorBoundary<T extends Record<string, any>>(
  Component: React.ComponentType<T>,
  errorBoundaryProps?: Omit<RouteErrorBoundaryProps, 'children'>
) {
  const WrappedComponent = (props: T) => (
    <RouteErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </RouteErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}

/**
 * Specific error boundary for API errors
 */
export function APIErrorBoundary({ children }: { children: React.ReactNode }) {
  const handleAPIError = (error: Error, errorInfo: React.ErrorInfo) => {
    // Special handling for API errors
    console.error('API Error Boundary:', error, errorInfo);
  };

  return (
    <RouteErrorBoundary
      onError={handleAPIError}
      fallback={({ error, resetErrorBoundary }) => (
        <div className='rounded-md bg-red-50 p-4'>
          <div className='flex'>
            <div className='flex-shrink-0'>
              <AlertTriangleIcon className='h-5 w-5 text-red-400' />
            </div>
            <div className='ml-3'>
              <h3 className='text-sm font-medium text-red-800'>API Error</h3>
              <div className='mt-2 text-sm text-red-700'>
                <p>{error.message || 'Failed to load data from the server.'}</p>
              </div>
              <div className='mt-4'>
                <button
                  type='button'
                  onClick={resetErrorBoundary}
                  className='bg-red-100 px-2 py-1.5 rounded-md text-sm font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-red-50 focus:ring-red-600'
                >
                  Retry
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    >
      {children}
    </RouteErrorBoundary>
  );
}
