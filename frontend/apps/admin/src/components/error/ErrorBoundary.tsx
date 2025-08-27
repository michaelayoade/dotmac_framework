/**
 * Comprehensive Error Boundary - Catches and handles React errors gracefully
 * Provides fallback UI and error reporting capabilities
 */

'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangleIcon, RefreshCwIcon, BugIcon, HelpCircleIcon } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  eventId?: string;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  resetOnPropsChange?: boolean;
  resetKeys?: Array<string | number>;
  isolateErrors?: boolean;
  level?: 'page' | 'section' | 'component';
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private resetTimeoutId: number | null = null;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const eventId = this.logError(error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
      eventId,
    });

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    const { resetOnPropsChange, resetKeys } = this.props;
    const { hasError } = this.state;

    // Reset error boundary when resetKeys change
    if (hasError && resetOnPropsChange && resetKeys) {
      const prevResetKeys = prevProps.resetKeys || [];
      const hasResetKeyChanged = resetKeys.some(
        (key, index) => key !== prevResetKeys[index]
      );

      if (hasResetKeyChanged) {
        this.resetErrorBoundary();
      }
    }
  }

  componentWillUnmount() {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }
  }

  logError = (error: Error, errorInfo: ErrorInfo): string => {
    const eventId = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Enhanced error logging
    const errorReport = {
      eventId,
      timestamp: new Date().toISOString(),
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      errorInfo: {
        componentStack: errorInfo.componentStack,
      },
      context: {
        level: this.props.level || 'component',
        url: typeof window !== 'undefined' ? window.location.href : 'unknown',
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
      },
    };

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.group(`🚨 Error Boundary Caught Error (${eventId})`);
      console.error('Error:', error);
      console.error('Component Stack:', errorInfo.componentStack);
      console.error('Full Report:', errorReport);
      console.groupEnd();
    }

    // TODO: Send to error reporting service in production
    // this.sendErrorReport(errorReport);

    return eventId;
  };

  resetErrorBoundary = () => {
    this.setState({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      eventId: undefined,
    });
  };

  handleRetry = () => {
    this.resetErrorBoundary();
  };

  handleAutoRetry = () => {
    // Implement exponential backoff for auto-retry
    this.resetTimeoutId = window.setTimeout(() => {
      this.resetErrorBoundary();
    }, 3000);
  };

  render() {
    const { hasError, error, errorInfo, eventId } = this.state;
    const { children, fallback, level = 'component', isolateErrors = false } = this.props;

    if (hasError) {
      // Return custom fallback if provided
      if (fallback) {
        return fallback;
      }

      // Return appropriate error UI based on level
      return this.renderErrorUI(error, errorInfo, eventId, level, isolateErrors);
    }

    return children;
  }

  private renderErrorUI(
    error?: Error,
    errorInfo?: ErrorInfo,
    eventId?: string,
    level: string = 'component',
    isolateErrors: boolean = false
  ) {
    switch (level) {
      case 'page':
        return <PageErrorFallback 
          error={error} 
          eventId={eventId} 
          onRetry={this.handleRetry} 
          onAutoRetry={this.handleAutoRetry}
        />;
      case 'section':
        return <SectionErrorFallback 
          error={error} 
          eventId={eventId} 
          onRetry={this.handleRetry}
          isolateErrors={isolateErrors}
        />;
      default:
        return <ComponentErrorFallback 
          error={error} 
          eventId={eventId} 
          onRetry={this.handleRetry}
        />;
    }
  }
}

// Page-level error fallback
function PageErrorFallback({ 
  error, 
  eventId, 
  onRetry, 
  onAutoRetry 
}: { 
  error?: Error; 
  eventId?: string; 
  onRetry: () => void;
  onAutoRetry: () => void;
}) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <AlertTriangleIcon className="w-8 h-8 text-red-600" />
        </div>
        
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Something went wrong
        </h1>
        
        <p className="text-gray-600 mb-6">
          We apologize for the inconvenience. An unexpected error occurred while loading this page.
        </p>
        
        <div className="space-y-3">
          <button
            onClick={onRetry}
            className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            <RefreshCwIcon className="w-4 h-4 mr-2" />
            Try Again
          </button>
          
          <button
            onClick={onAutoRetry}
            className="w-full flex items-center justify-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-medium"
          >
            Auto-retry in 3 seconds
          </button>
          
          <button
            onClick={() => window.location.reload()}
            className="w-full text-gray-500 hover:text-gray-700 text-sm"
          >
            Reload Page
          </button>
        </div>

        {process.env.NODE_ENV === 'development' && error && (
          <details className="mt-6 text-left">
            <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
              Technical Details
            </summary>
            <div className="mt-2 p-3 bg-gray-50 rounded text-xs font-mono text-red-600 overflow-auto max-h-40">
              <div className="mb-2">
                <strong>Error:</strong> {error.message}
              </div>
              <div>
                <strong>Event ID:</strong> {eventId}
              </div>
            </div>
          </details>
        )}
      </div>
    </div>
  );
}

// Section-level error fallback
function SectionErrorFallback({ 
  error, 
  eventId, 
  onRetry,
  isolateErrors = false
}: { 
  error?: Error; 
  eventId?: string; 
  onRetry: () => void;
  isolateErrors?: boolean;
}) {
  return (
    <div className={`bg-red-50 border border-red-200 rounded-lg p-6 ${isolateErrors ? 'min-h-[200px]' : ''}`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <BugIcon className="w-5 h-5 text-red-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-medium text-red-800 mb-2">
            Section Unavailable
          </h3>
          <p className="text-sm text-red-700 mb-4">
            This section encountered an error and couldn't load properly.
          </p>
          <div className="flex space-x-3">
            <button
              onClick={onRetry}
              className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded text-red-700 bg-white hover:bg-red-50"
            >
              <RefreshCwIcon className="w-3 h-3 mr-1.5" />
              Retry
            </button>
            {process.env.NODE_ENV === 'development' && (
              <span className="text-xs text-red-600">
                Event ID: {eventId}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Component-level error fallback
function ComponentErrorFallback({ 
  error, 
  eventId, 
  onRetry 
}: { 
  error?: Error; 
  eventId?: string; 
  onRetry: () => void;
}) {
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
      <div className="flex items-center space-x-2">
        <HelpCircleIcon className="w-4 h-4 text-yellow-600 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-yellow-800">
            Component error occurred
          </p>
        </div>
        <button
          onClick={onRetry}
          className="text-yellow-800 hover:text-yellow-900 text-xs underline flex-shrink-0"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

// Specialized error boundaries for specific use cases
export function BillingErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      level="section"
      isolateErrors={true}
      onError={(error, errorInfo) => {
        // Billing-specific error handling
        console.error('Billing component error:', error);
        // TODO: Send to billing error monitoring
      }}
      fallback={
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <AlertTriangleIcon className="w-6 h-6 text-red-600" />
            <div>
              <h3 className="text-lg font-medium text-red-800">Billing Service Error</h3>
              <p className="text-sm text-red-600 mt-1">
                The billing system is temporarily unavailable. Please try again in a few moments.
              </p>
            </div>
          </div>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}

export function ApiErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      level="component"
      onError={(error, errorInfo) => {
        // API-specific error handling
        console.error('API component error:', error);
      }}
      fallback={
        <div className="bg-blue-50 border border-blue-200 rounded p-3">
          <div className="flex items-center space-x-2">
            <RefreshCwIcon className="w-4 h-4 text-blue-600" />
            <span className="text-sm text-blue-800">Loading failed. Please refresh.</span>
          </div>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}

// Hook for manual error reporting
export function useErrorHandler() {
  return (error: Error, errorInfo?: any) => {
    // Manual error reporting
    console.error('Manual error report:', error, errorInfo);
    // TODO: Send to error reporting service
  };
}

export default ErrorBoundary;