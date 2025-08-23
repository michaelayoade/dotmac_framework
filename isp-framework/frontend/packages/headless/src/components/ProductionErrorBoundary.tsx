'use client';

import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showDetails?: boolean;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

/**
 * Production-ready error boundary with ISP-specific error handling
 */
export class ProductionErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler
    this.props.onError?.(error, errorInfo);

    // Log error to monitoring service in production
    if (typeof window !== 'undefined' && process.env.NODE_ENV === 'production') {
      this.logErrorToService(error, errorInfo);
    }
  }

  private logErrorToService(error: Error, errorInfo: ErrorInfo) {
    try {
      // In production, send to monitoring service
      const errorData = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        userId: this.getCurrentUserId(),
        tenantId: this.getCurrentTenantId(),
      };

      // Send to error tracking service (DataDog, Sentry, etc.)
      fetch('/api/v1/errors/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorData),
      }).catch(console.error);
    } catch (loggingError) {
      console.error('Failed to log error to service:', loggingError);
    }
  }

  private getCurrentUserId(): string | null {
    try {
      const user = JSON.parse(localStorage.getItem('dotmac_user') || 'null');
      return user?.id || null;
    } catch {
      return null;
    }
  }

  private getCurrentTenantId(): string | null {
    try {
      const tenant = JSON.parse(localStorage.getItem('dotmac_tenant') || 'null');
      return tenant?.id || null;
    } catch {
      return null;
    }
  }

  private getErrorCategory(error: Error): string {
    if (error.name === 'ChunkLoadError' || error.message.includes('Loading chunk')) {
      return 'chunk_load_error';
    }
    if (error.message.includes('Network Error') || error.message.includes('fetch')) {
      return 'network_error';
    }
    if (error.message.includes('authentication') || error.message.includes('Unauthorized')) {
      return 'auth_error';
    }
    if (error.message.includes('payment') || error.message.includes('billing')) {
      return 'payment_error';
    }
    return 'unknown_error';
  }

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
    });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleReportIssue = () => {
    const { error } = this.state;
    const errorCategory = error ? this.getErrorCategory(error) : 'unknown';
    
    const subject = encodeURIComponent(`ISP Portal Error Report - ${errorCategory}`);
    const body = encodeURIComponent(
      `Error Details:\n\n` +
      `Message: ${error?.message}\n` +
      `Category: ${errorCategory}\n` +
      `Time: ${new Date().toISOString()}\n` +
      `Page: ${window.location.href}\n\n` +
      `Please describe what you were doing when this error occurred:`
    );
    
    window.open(`mailto:support@dotmac.com?subject=${subject}&body=${body}`);
  };

  public render() {
    if (this.state.hasError) {
      // Show custom fallback UI if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { error } = this.state;
      const errorCategory = error ? this.getErrorCategory(error) : 'unknown';
      const { showDetails = false } = this.props;

      return (
        <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
          <div className="sm:mx-auto sm:w-full sm:max-w-md">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
              <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.098 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              Something went wrong
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              {errorCategory === 'chunk_load_error' && 
                'Failed to load application components. This usually happens after an update.'}
              {errorCategory === 'network_error' && 
                'Unable to connect to the server. Please check your internet connection.'}
              {errorCategory === 'auth_error' && 
                'Authentication error occurred. You may need to sign in again.'}
              {errorCategory === 'payment_error' && 
                'Payment processing error occurred. Please try again or contact support.'}
              {errorCategory === 'unknown_error' && 
                'An unexpected error occurred. Our team has been notified.'}
            </p>
          </div>

          <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
            <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
              <div className="space-y-4">
                <button
                  onClick={this.handleRetry}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Try Again
                </button>

                {errorCategory === 'chunk_load_error' && (
                  <button
                    onClick={this.handleReload}
                    className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Reload Application
                  </button>
                )}

                {errorCategory === 'auth_error' && (
                  <button
                    onClick={() => {
                      localStorage.clear();
                      window.location.href = '/login';
                    }}
                    className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Sign In Again
                  </button>
                )}

                <button
                  onClick={this.handleReportIssue}
                  className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Report Issue
                </button>
              </div>

              {showDetails && error && (
                <details className="mt-6">
                  <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
                    Technical Details
                  </summary>
                  <div className="mt-2 p-3 bg-gray-100 rounded text-xs text-gray-700 font-mono overflow-auto max-h-40">
                    <div><strong>Error:</strong> {error.message}</div>
                    {error.stack && (
                      <div className="mt-2">
                        <strong>Stack:</strong>
                        <pre className="mt-1">{error.stack}</pre>
                      </div>
                    )}
                  </div>
                </details>
              )}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Convenience wrapper for common ISP portal error scenarios
export const ISPErrorBoundary: React.FC<{
  children: ReactNode;
  portal?: 'admin' | 'customer' | 'reseller' | 'technician';
}> = ({ children, portal = 'admin' }) => (
  <ProductionErrorBoundary
    onError={(error, errorInfo) => {
      console.error(`${portal} Portal Error:`, error, errorInfo);
    }}
    showDetails={process.env.NODE_ENV === 'development'}
  >
    {children}
  </ProductionErrorBoundary>
);

export default ProductionErrorBoundary;