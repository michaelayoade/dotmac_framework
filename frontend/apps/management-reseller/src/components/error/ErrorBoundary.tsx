'use client';

import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { queryClient } from '@/lib/query-client';

interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
  resetKeys?: Array<unknown>;
}

function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  const router = useRouter();

  const handleGoHome = () => {
    router.push('/dashboard');
    resetErrorBoundary();
  };

  const handleRetry = () => {
    // Clear React Query cache to ensure fresh data
    queryClient.clear();
    resetErrorBoundary();
  };

  const isDevelopment = process.env.NODE_ENV === 'development';

  return (
    <div className="min-h-96 flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="mx-auto flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
          <AlertTriangle className="w-8 h-8 text-red-600" />
        </div>
        
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Something went wrong
        </h2>
        
        <p className="text-gray-600 mb-6">
          {isDevelopment 
            ? error.message || 'An unexpected error occurred'
            : 'An unexpected error occurred. Our team has been notified and is working to fix this issue.'
          }
        </p>

        {isDevelopment && error.stack && (
          <details className="mb-6 text-left">
            <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700 mb-2">
              View technical details
            </summary>
            <pre className="text-xs bg-gray-100 p-3 rounded border overflow-auto max-h-40 text-gray-800">
              {error.stack}
            </pre>
          </details>
        )}
        
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={handleRetry}
            className="management-button-primary flex items-center justify-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
          
          <button
            onClick={handleGoHome}
            className="management-button-secondary flex items-center justify-center gap-2"
          >
            <Home className="w-4 h-4" />
            Go to Dashboard
          </button>
        </div>

        <p className="text-xs text-gray-400 mt-6">
          Error ID: {error.name}-{Date.now()}
        </p>
      </div>
    </div>
  );
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: any) => void;
  resetKeys?: Array<unknown>;
}

export function ErrorBoundary({ 
  children, 
  fallback, 
  onError,
  resetKeys 
}: ErrorBoundaryProps) {
  const handleError = async (error: Error, errorInfo: any) => {
    // Log error for monitoring
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // Send to comprehensive error reporting service
    try {
      const { errorReporter } = await import('@/lib/error-handling/error-reporter');
      const { ErrorRecoveryStrategies } = await import('@/lib/error-handling/recovery-strategies');
      
      const userContext = errorReporter.getCurrentUserContext();
      await errorReporter.reportComponentError(error, errorInfo, {
        component: 'error_boundary',
        ...(userContext.id && userContext.email && userContext.role ? { user: userContext as { id: string; email: string; role: string; } } : {})
      });

      // Attempt recovery
      const recoveryResult = await ErrorRecoveryStrategies.recoverFromComponentError(
        error,
        { errorInfo }
      );

      if (recoveryResult.shouldRetry && recoveryResult.retryDelay) {
        // Schedule automatic retry if recommended
        console.info(`Scheduling error boundary retry in ${recoveryResult.retryDelay}ms`);
      }
    } catch (reportingError) {
      console.error('Failed to report error to comprehensive system:', reportingError);
    }
    
    // Call custom error handler if provided
    onError?.(error, errorInfo);
  };

  const handleReset = () => {
    // Clear React Query cache on reset
    queryClient.clear();
  };

  return (
    <ReactErrorBoundary
      FallbackComponent={fallback || ErrorFallback}
      onError={handleError}
      onReset={handleReset}
      resetKeys={resetKeys || []}
    >
      {children}
    </ReactErrorBoundary>
  );
}

// Route-level error boundary for specific pages
export function RouteErrorBoundary({ 
  children, 
  routeName 
}: { 
  children: React.ReactNode;
  routeName: string;
}) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error(`Error in ${routeName} route:`, error, errorInfo);
      }}
      resetKeys={[routeName]}
    >
      {children}
    </ErrorBoundary>
  );
}

// Query error boundary for data fetching errors
export function QueryErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary
      fallback={({ error, resetErrorBoundary }) => (
        <div className="p-4 border border-red-200 rounded-lg bg-red-50">
          <div className="flex items-center gap-2 text-red-800 mb-2">
            <AlertTriangle className="w-4 h-4" />
            <span className="font-medium">Failed to load data</span>
          </div>
          <p className="text-red-700 text-sm mb-3">
            {error.message || 'Unable to fetch the required data.'}
          </p>
          <button
            onClick={resetErrorBoundary}
            className="text-sm bg-red-100 hover:bg-red-200 text-red-800 px-3 py-1 rounded border border-red-300 transition-colors"
          >
            Retry
          </button>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

// Component-level error boundary for isolating failures
export function ComponentErrorBoundary({ 
  children, 
  componentName 
}: { 
  children: React.ReactNode;
  componentName?: string;
}) {
  return (
    <ErrorBoundary
      fallback={({ error, resetErrorBoundary }) => (
        <div className="p-3 border border-orange-200 rounded bg-orange-50">
          <div className="flex items-center gap-2 text-orange-800 mb-1">
            <AlertTriangle className="w-3 h-3" />
            <span className="text-xs font-medium">
              {componentName ? `${componentName} Error` : 'Component Error'}
            </span>
          </div>
          <p className="text-orange-700 text-xs mb-2">
            This component failed to render properly.
          </p>
          <button
            onClick={resetErrorBoundary}
            className="text-xs bg-orange-100 hover:bg-orange-200 text-orange-800 px-2 py-1 rounded"
          >
            Retry
          </button>
        </div>
      )}
      onError={(error, errorInfo) => {
        console.error(`Component error in ${componentName || 'unknown'}:`, error, errorInfo);
      }}
    >
      {children}
    </ErrorBoundary>
  );
}

// Auth error boundary for authentication-related errors
export function AuthErrorBoundary({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  return (
    <ErrorBoundary
      fallback={({ error, resetErrorBoundary }) => (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="text-center max-w-sm">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Authentication Error
            </h2>
            <p className="text-gray-600 mb-6">
              There was a problem with your authentication. Please sign in again.
            </p>
            <button
              onClick={() => router.push('/login')}
              className="management-button-primary"
            >
              Go to Login
            </button>
          </div>
        </div>
      )}
      onError={(error, errorInfo) => {
        console.error('Authentication error:', error, errorInfo);
        // Clear auth state on auth errors
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth');
          sessionStorage.clear();
        }
      }}
    >
      {children}
    </ErrorBoundary>
  );
}