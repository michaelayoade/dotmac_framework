'use client';

import { AlertCircle, Home, Mail, RefreshCw } from 'lucide-react';
import React, { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  level?: 'component' | 'page' | 'application';
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string;
}

class CustomerErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
      errorId: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details
    console.error('[CustomerErrorBoundary] Caught error:', error);
    console.error('[CustomerErrorBoundary] Error info:', errorInfo);

    // Report to Sentry with error tracking
    if (typeof window !== 'undefined') {
      import('../../lib/monitoring/errorTracking').then(
        ({ ErrorTracker, ErrorCategory, ErrorSeverity }) => {
          ErrorTracker.reportError(error, {
            category: ErrorCategory.UI,
            severity: ErrorSeverity.HIGH,
            component: 'error-boundary',
            metadata: {
              componentStack: errorInfo.componentStack,
              errorBoundaryLevel: this.props.level || 'component',
            },
          });
        }
      );
    }

    // Update state with error info
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Report error to analytics/monitoring service
    this.reportError(error, errorInfo);
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    try {
      // Send error to monitoring service (implement based on your analytics setup)
      if (typeof window !== 'undefined' && window.gtag) {
        window.gtag('event', 'exception', {
          description: `${error.name}: ${error.message}`,
          fatal: this.props.level === 'application',
          error_id: this.state.errorId,
        });
      }

      // Log structured error for debugging
      const errorReport = {
        timestamp: new Date().toISOString(),
        errorId: this.state.errorId,
        level: this.props.level || 'component',
        error: {
          name: error.name,
          message: error.message,
          stack: error.stack,
        },
        errorInfo: {
          componentStack: errorInfo.componentStack,
        },
        userAgent: navigator.userAgent,
        url: window.location.href,
      };

      console.error('[CustomerErrorBoundary] Error report:', errorReport);
    } catch (reportingError) {
      console.error('[CustomerErrorBoundary] Failed to report error:', reportingError);
    }
  };

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
    });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { level = 'component' } = this.props;
      const { error, errorId } = this.state;

      return (
        <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
          <div className="sm:mx-auto sm:w-full sm:max-w-md">
            <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
              <div className="text-center">
                <AlertCircle className="mx-auto h-12 w-12 text-red-500" />
                <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                  {level === 'application' ? 'Application Error' : 'Something went wrong'}
                </h2>
                <p className="mt-2 text-center text-sm text-gray-600">
                  {level === 'application'
                    ? 'The application encountered an unexpected error.'
                    : 'We encountered an unexpected error while loading this section.'}
                </p>
              </div>

              {process.env.NODE_ENV === 'development' && error && (
                <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-md">
                  <h3 className="text-sm font-medium text-red-800 mb-2">
                    Error Details (Development Only)
                  </h3>
                  <p className="text-xs text-red-700 font-mono">
                    {error.name}: {error.message}
                  </p>
                  {error.stack && (
                    <details className="mt-2">
                      <summary className="text-xs text-red-600 cursor-pointer">Stack Trace</summary>
                      <pre className="mt-2 text-xs text-red-700 whitespace-pre-wrap overflow-x-auto">
                        {error.stack}
                      </pre>
                    </details>
                  )}
                </div>
              )}

              <div className="mt-6">
                <div className="text-center text-xs text-gray-500 mb-4">Error ID: {errorId}</div>

                <div className="space-y-3">
                  {level === 'component' && (
                    <button
                      onClick={this.handleRetry}
                      className="w-full flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Try Again
                    </button>
                  )}

                  <button
                    onClick={this.handleReload}
                    className="w-full flex justify-center items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Reload Page
                  </button>

                  {level !== 'application' && (
                    <button
                      onClick={this.handleGoHome}
                      className="w-full flex justify-center items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <Home className="h-4 w-4 mr-2" />
                      Go to Dashboard
                    </button>
                  )}
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="text-center">
                  <p className="text-sm text-gray-600 mb-2">
                    If this problem persists, please contact support.
                  </p>
                  <a
                    href="mailto:support@dotmac.com?subject=Customer Portal Error&body=Error ID: {errorId}"
                    className="inline-flex items-center text-sm text-blue-600 hover:text-blue-500"
                  >
                    <Mail className="h-4 w-4 mr-1" />
                    Email Support
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default CustomerErrorBoundary;

// Convenience wrapper components for different error boundary levels
export function ComponentErrorBoundary({
  children,
  onError,
}: {
  children: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}) {
  return (
    <CustomerErrorBoundary level="component" onError={onError}>
      {children}
    </CustomerErrorBoundary>
  );
}

export function PageErrorBoundary({
  children,
  onError,
}: {
  children: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}) {
  return (
    <CustomerErrorBoundary level="page" onError={onError}>
      {children}
    </CustomerErrorBoundary>
  );
}

export function ApplicationErrorBoundary({
  children,
  onError,
}: {
  children: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}) {
  return (
    <CustomerErrorBoundary level="application" onError={onError}>
      {children}
    </CustomerErrorBoundary>
  );
}
