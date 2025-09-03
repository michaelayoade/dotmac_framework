'use client';

import React from 'react';
import { QueryErrorResetBoundary } from '@tanstack/react-query';
import { RouteErrorBoundary } from './RouteErrorBoundary';
import { ExclamationTriangleIcon, ArrowPathIcon, ServerIcon } from '@heroicons/react/24/outline';
import { api } from '@/lib/http';

interface QueryErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

function QueryErrorFallback({ error, resetErrorBoundary }: QueryErrorFallbackProps) {
  // Check if it's a network error
  const isNetworkError =
    error.message.includes('Network') ||
    error.message.includes('fetch') ||
    error.message.includes('ECONNREFUSED');

  // Check if it's a server error (5xx)
  const isServerError =
    error.message.includes('500') ||
    error.message.includes('502') ||
    error.message.includes('503') ||
    error.message.includes('504');

  const getErrorIcon = () => {
    if (isNetworkError) return ServerIcon;
    if (isServerError) return ServerIcon;
    return ExclamationTriangleIcon;
  };

  const getErrorTitle = () => {
    if (isNetworkError) return 'Connection Problem';
    if (isServerError) return 'Server Error';
    return 'Data Loading Error';
  };

  const getErrorMessage = () => {
    if (isNetworkError) {
      return 'Unable to connect to the server. Please check your internet connection and try again.';
    }
    if (isServerError) {
      return 'The server is experiencing issues. Please try again in a few moments.';
    }
    return error.message || 'Failed to load data. Please try again.';
  };

  const ErrorIcon = getErrorIcon();

  return (
    <div className='rounded-lg bg-white border border-gray-200 p-6'>
      <div className='text-center'>
        <ErrorIcon className='mx-auto h-12 w-12 text-gray-400' />
        <h3 className='mt-4 text-lg font-medium text-gray-900'>{getErrorTitle()}</h3>
        <p className='mt-2 text-sm text-gray-600'>{getErrorMessage()}</p>

        {/* Development error details */}
        {process.env.NODE_ENV === 'development' && (
          <details className='mt-4 text-left'>
            <summary className='cursor-pointer text-sm text-gray-500 hover:text-gray-700'>
              Technical Details (Dev Mode)
            </summary>
            <div className='mt-2 p-3 bg-gray-50 rounded-md'>
              <pre className='text-xs text-gray-700 whitespace-pre-wrap'>
                {error.stack || error.message}
              </pre>
            </div>
          </details>
        )}

        <div className='mt-6'>
          <button
            onClick={resetErrorBoundary}
            className='inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500'
          >
            <ArrowPathIcon className='h-4 w-4 mr-2' />
            Try Again
          </button>
        </div>

        {isNetworkError && (
          <div className='mt-4 text-xs text-gray-500'>
            <p>Troubleshooting tips:</p>
            <ul className='mt-1 text-left list-disc list-inside space-y-1'>
              <li>Check your internet connection</li>
              <li>Disable VPN if you're using one</li>
              <li>Try refreshing the page</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

interface QueryErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<QueryErrorFallbackProps>;
}

/**
 * Error boundary specifically for React Query errors
 * Integrates with React Query's error reset functionality
 */
export function QueryErrorBoundary({
  children,
  fallback = QueryErrorFallback,
}: QueryErrorBoundaryProps) {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <RouteErrorBoundary
          onError={(error) => {
            console.error('Query Error Boundary caught error:', error);

            // SECURITY FIX: Enhanced error tracking and audit logging
            if (typeof window !== 'undefined') {
              // Send to audit logging system
              try {
                const auditLogger = require('@/lib/audit-logger').getAuditLogger();
                auditLogger
                  .logSecurity(
                    require('@/lib/audit-logger').AuditEventType.SYSTEM_ERROR,
                    `React Query Error: ${error.message}`,
                    {
                      applicationName: 'DotMac Management Admin Portal',
                      environment: process.env.NODE_ENV || 'development',
                      resourceType: 'query_error',
                    },
                    {
                      reason: 'react_query_error',
                      customData: {
                        errorMessage: error.message,
                        errorName: error.name,
                        errorStack: error.stack?.substring(0, 2000),
                        timestamp: new Date().toISOString(),
                        url: window.location.href,
                        userAgent: window.navigator.userAgent,
                      },
                    }
                  )
                  .catch(console.error);
              } catch (auditError) {
                console.warn('Failed to log query error to audit system:', auditError);
              }

              // Send to monitoring service with rate limiting
              const errorKey = `query_error_${error.message}_${Date.now()}`;
              const lastErrorTime = sessionStorage.getItem(`last_error_${errorKey}`);
              const now = Date.now();

              // Rate limit: only send same error once per 5 minutes
              if (!lastErrorTime || now - parseInt(lastErrorTime) > 300000) {
                sessionStorage.setItem(`last_error_${errorKey}`, now.toString());

                api
                  .post('/api/monitoring/query-error', {
                    type: 'query_error_boundary',
                    error: {
                      message: error.message,
                      stack: error.stack,
                      name: error.name,
                    },
                    metadata: {
                      timestamp: new Date().toISOString(),
                      url: window.location.href,
                      userAgent: window.navigator.userAgent,
                      errorKey,
                    },
                  })
                  .catch(console.error);
              }
            }
          }}
          fallback={({ error, resetErrorBoundary }) => {
            const handleReset = () => {
              reset(); // Reset React Query errors
              resetErrorBoundary(); // Reset error boundary
            };

            return React.createElement(fallback, { error, resetErrorBoundary: handleReset });
          }}
        >
          {children}
        </RouteErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}

/**
 * Smaller inline error boundary for individual components
 */
export function InlineErrorBoundary({
  children,
  fallbackMessage = 'Something went wrong with this component',
}: {
  children: React.ReactNode;
  fallbackMessage?: string;
}) {
  return (
    <RouteErrorBoundary
      fallback={({ resetErrorBoundary }) => (
        <div className='rounded-md bg-yellow-50 p-4'>
          <div className='flex'>
            <div className='flex-shrink-0'>
              <ExclamationTriangleIcon className='h-5 w-5 text-yellow-400' />
            </div>
            <div className='ml-3'>
              <p className='text-sm text-yellow-700'>{fallbackMessage}</p>
              <div className='mt-2'>
                <button
                  type='button'
                  onClick={resetErrorBoundary}
                  className='text-sm font-medium text-yellow-700 underline hover:text-yellow-600'
                >
                  Try again
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
