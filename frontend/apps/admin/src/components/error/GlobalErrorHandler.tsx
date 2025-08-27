/**
 * Global Error Handler for the Admin Application
 * Provides centralized error handling, reporting, and user feedback
 */

'use client';

import { useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import { ErrorBoundary } from '@dotmac/primitives/error';

interface GlobalErrorHandlerProps {
  children: ReactNode;
}

export function GlobalErrorHandler({ children }: GlobalErrorHandlerProps) {
  // Handle unhandled promise rejections
  const handleUnhandledRejection = useCallback((event: PromiseRejectionEvent) => {
    console.error('🚨 Unhandled Promise Rejection:', event.reason);
    
    // Report to error tracking
    reportError(new Error(`Unhandled Promise Rejection: ${event.reason}`), {
      type: 'unhandledRejection',
      reason: event.reason,
    });

    // Prevent default browser behavior
    event.preventDefault();
  }, []);

  // Handle general JavaScript errors
  const handleError = useCallback((event: ErrorEvent) => {
    console.error('🚨 JavaScript Error:', event.error);
    
    reportError(event.error || new Error(event.message), {
      type: 'javascriptError',
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    });
  }, []);

  // Setup global error listeners
  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('unhandledrejection', handleUnhandledRejection);
      window.addEventListener('error', handleError);

      return () => {
        window.removeEventListener('unhandledrejection', handleUnhandledRejection);
        window.removeEventListener('error', handleError);
      };
    }
  }, [handleUnhandledRejection, handleError]);

  // Main error handler for React error boundaries
  const handleReactError = useCallback((error: Error, errorInfo: React.ErrorInfo, errorId: string) => {
    reportError(error, {
      type: 'reactError',
      errorId,
      componentStack: errorInfo.componentStack,
    });
  }, []);

  return (
    <ErrorBoundary level="page" onError={handleReactError} showErrorDetails={process.env.NODE_ENV === 'development'}>
      {children}
    </ErrorBoundary>
  );
}

// Centralized error reporting function
function reportError(error: Error, context: Record<string, any> = {}) {
  const errorReport = {
    message: error.message,
    stack: error.stack,
    timestamp: new Date().toISOString(),
    url: typeof window !== 'undefined' ? window.location.href : 'unknown',
    userAgent: typeof window !== 'undefined' ? navigator.userAgent : 'unknown',
    context,
  };

  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.group('🚨 Error Report');
    console.error('Error:', error);
    console.log('Context:', context);
    console.log('Full Report:', errorReport);
    console.groupEnd();
  }

  // Send to error tracking service
  if (typeof window !== 'undefined') {
    try {
      // This could be Sentry, LogRocket, or custom endpoint
      fetch('/api/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorReport),
      }).catch(() => {
        // Fail silently to avoid infinite error loops
      });
    } catch {
      // Fail silently
    }
  }
}

// Custom hook for manual error reporting
export function useErrorReporter() {
  return useCallback((error: Error, context?: Record<string, any>) => {
    reportError(error, context);
  }, []);
}

// HOC for wrapping components with error boundaries
export function withErrorHandler<P extends object>(
  Component: React.ComponentType<P>,
  level: 'page' | 'section' | 'component' = 'component'
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary level={level}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorHandler(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}

// Specific error fallback components for common scenarios
export function NetworkErrorFallback({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="mb-4 rounded-full bg-orange-100 p-3">
        <svg className="h-8 w-8 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="mb-2 text-lg font-semibold text-gray-900">Network Error</h3>
      <p className="mb-4 text-gray-600">Unable to connect to the server. Please check your connection.</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function LoadingErrorFallback({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="mb-4 rounded-full bg-red-100 p-3">
        <svg className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
      <h3 className="mb-2 text-lg font-semibold text-gray-900">Loading Failed</h3>
      <p className="mb-4 text-gray-600">This content failed to load properly.</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Try Again
        </button>
      )}
    </div>
  );
}