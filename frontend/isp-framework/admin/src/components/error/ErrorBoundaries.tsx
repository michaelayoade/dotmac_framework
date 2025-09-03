/**
 * Enhanced Error Boundaries
 * Modular error boundaries for different application sections
 */

'use client';

import React, { type ReactNode, type ErrorInfo } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug, Wifi, WifiOff } from 'lucide-react';
import { showErrorNotification } from '../../stores/appStore';

// Base error boundary state
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string | null;
}

// Error boundary levels for different granularity
export type ErrorBoundaryLevel = 'app' | 'page' | 'section' | 'component';

// Error boundary props
interface ErrorBoundaryProps {
  children: ReactNode;
  level?: ErrorBoundaryLevel;
  fallback?: (error: Error, errorInfo: ErrorInfo, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo, errorId: string) => void;
  showErrorDetails?: boolean;
}

// Base Error Boundary Class
class BaseErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);

    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    const errorId = `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    return {
      hasError: true,
      error,
      errorId,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    // Log error for debugging
    console.error('Error Boundary caught an error:', error, errorInfo);

    // Generate error ID for tracking
    const errorId = this.state.errorId || `error-${Date.now()}`;

    // Call custom error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo, errorId);
    }

    // Report error to monitoring service
    this.reportError(error, errorInfo, errorId);
  }

  private reportError = (error: Error, errorInfo: ErrorInfo, errorId: string) => {
    // Report to external error tracking service
    if (typeof window !== 'undefined') {
      try {
        fetch('/api/errors', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            errorId,
            message: error.message,
            stack: error.stack,
            componentStack: errorInfo.componentStack,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            level: this.props.level || 'component',
          }),
        }).catch(() => {
          // Fail silently to avoid infinite error loops
        });
      } catch {
        // Fail silently
      }
    }
  };

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
    });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.state.errorInfo!, this.handleReset);
      }

      // Use default fallback based on level
      return this.getDefaultFallback();
    }

    return this.props.children;
  }

  private getDefaultFallback() {
    const { level = 'component', showErrorDetails = false } = this.props;
    const { error, errorInfo, errorId } = this.state;

    switch (level) {
      case 'app':
        return (
          <AppErrorFallback
            error={error!}
            errorInfo={errorInfo!}
            errorId={errorId!}
            onReset={this.handleReset}
            showErrorDetails={showErrorDetails}
          />
        );

      case 'page':
        return (
          <PageErrorFallback
            error={error!}
            errorInfo={errorInfo!}
            errorId={errorId!}
            onReset={this.handleReset}
            showErrorDetails={showErrorDetails}
          />
        );

      case 'section':
        return (
          <SectionErrorFallback
            error={error!}
            errorInfo={errorInfo!}
            errorId={errorId!}
            onReset={this.handleReset}
            showErrorDetails={showErrorDetails}
          />
        );

      default:
        return (
          <ComponentErrorFallback
            error={error!}
            errorInfo={errorInfo!}
            errorId={errorId!}
            onReset={this.handleReset}
            showErrorDetails={showErrorDetails}
          />
        );
    }
  }
}

// Error fallback components
interface ErrorFallbackProps {
  error: Error;
  errorInfo: ErrorInfo;
  errorId: string;
  onReset: () => void;
  showErrorDetails: boolean;
}

function AppErrorFallback({ error, errorId, onReset, showErrorDetails }: ErrorFallbackProps) {
  return (
    <div className='min-h-screen flex items-center justify-center bg-gray-50 px-4'>
      <div className='max-w-md w-full'>
        <div className='bg-white shadow-lg rounded-lg p-8 text-center'>
          <div className='w-16 h-16 mx-auto mb-6 bg-red-100 rounded-full flex items-center justify-center'>
            <AlertTriangle className='w-8 h-8 text-red-600' />
          </div>

          <h1 className='text-2xl font-bold text-gray-900 mb-4'>Oops! Something went wrong</h1>

          <p className='text-gray-600 mb-6'>
            We encountered an unexpected error. Our team has been notified and is working on a fix.
          </p>

          {showErrorDetails && (
            <div className='mb-6 p-4 bg-gray-50 rounded-lg text-left'>
              <details>
                <summary className='text-sm font-medium text-gray-700 cursor-pointer'>
                  Error Details (ID: {errorId})
                </summary>
                <div className='mt-2 text-xs text-gray-600 font-mono'>{error.message}</div>
              </details>
            </div>
          )}

          <div className='space-y-3'>
            <button
              onClick={onReset}
              className='w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500'
            >
              <RefreshCw className='w-4 h-4 mr-2' />
              Try Again
            </button>

            <button
              onClick={() => (window.location.href = '/')}
              className='w-full flex items-center justify-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50'
            >
              <Home className='w-4 h-4 mr-2' />
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function PageErrorFallback({ error, errorId, onReset, showErrorDetails }: ErrorFallbackProps) {
  return (
    <div className='flex items-center justify-center min-h-96 px-4'>
      <div className='max-w-md w-full text-center'>
        <div className='w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center'>
          <AlertTriangle className='w-6 h-6 text-red-600' />
        </div>

        <h2 className='text-xl font-semibold text-gray-900 mb-3'>Page Error</h2>

        <p className='text-gray-600 mb-4'>
          This page encountered an error and couldn't be displayed properly.
        </p>

        {showErrorDetails && (
          <div className='mb-4 p-3 bg-gray-50 rounded text-left text-xs'>
            <strong>Error ID:</strong> {errorId}
            <br />
            <strong>Message:</strong> {error.message}
          </div>
        )}

        <div className='flex flex-col sm:flex-row gap-2 justify-center'>
          <button
            onClick={onReset}
            className='flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700'
          >
            <RefreshCw className='w-4 h-4 mr-2' />
            Retry
          </button>

          <button
            onClick={() => window.history.back()}
            className='flex items-center justify-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50'
          >
            Go Back
          </button>
        </div>
      </div>
    </div>
  );
}

function SectionErrorFallback({ error, errorId, onReset }: ErrorFallbackProps) {
  return (
    <div className='bg-red-50 border border-red-200 rounded-lg p-6'>
      <div className='flex items-start'>
        <AlertTriangle className='w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0' />
        <div className='flex-1'>
          <h3 className='font-medium text-red-800 mb-1'>Section Error</h3>
          <p className='text-red-700 text-sm mb-3'>
            This section couldn't be loaded due to an error.
          </p>
          <div className='flex items-center gap-3'>
            <button
              onClick={onReset}
              className='text-sm bg-red-100 text-red-800 px-3 py-1 rounded hover:bg-red-200'
            >
              Try Again
            </button>
            <span className='text-xs text-red-600'>ID: {errorId}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ComponentErrorFallback({ error, errorId, onReset }: ErrorFallbackProps) {
  return (
    <div className='bg-yellow-50 border border-yellow-200 rounded p-4'>
      <div className='flex items-center'>
        <Bug className='w-4 h-4 text-yellow-600 mr-2 flex-shrink-0' />
        <div className='flex-1'>
          <span className='text-sm text-yellow-800'>Component Error</span>
          <button
            onClick={onReset}
            className='ml-3 text-xs text-yellow-700 underline hover:no-underline'
          >
            Retry
          </button>
        </div>
      </div>
    </div>
  );
}

// Network-specific error boundary
export function NetworkErrorBoundary({
  children,
  onRetry,
}: {
  children: ReactNode;
  onRetry?: () => void;
}) {
  return (
    <BaseErrorBoundary
      level='section'
      fallback={(error) => (
        <div className='flex flex-col items-center justify-center p-8 text-center'>
          <div className='mb-4 rounded-full bg-orange-100 p-3'>
            <WifiOff className='h-8 w-8 text-orange-600' />
          </div>
          <h3 className='mb-2 text-lg font-semibold text-gray-900'>Network Error</h3>
          <p className='mb-4 text-gray-600'>
            Unable to connect to the server. Please check your connection.
          </p>
          {onRetry && (
            <button
              onClick={onRetry}
              className='rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500'
            >
              <Wifi className='mr-2 inline h-4 w-4' />
              Retry Connection
            </button>
          )}
        </div>
      )}
    >
      {children}
    </BaseErrorBoundary>
  );
}

// Export the main error boundary
export function ErrorBoundary(props: ErrorBoundaryProps) {
  return <BaseErrorBoundary {...props} />;
}

// HOC for wrapping components with error boundaries
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  level: ErrorBoundaryLevel = 'component'
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary level={level}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}
