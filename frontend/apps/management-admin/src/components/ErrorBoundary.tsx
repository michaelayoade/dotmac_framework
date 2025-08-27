'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { getAuditLogger, AuditEventType } from '@/lib/audit-logger';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (_error: Error, _errorInfo: ErrorInfo) => void;
  isolateComponent?: boolean; // If true, only this component fails, not the whole app
  name?: string; // Component name for better tracking
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  errorId?: string;
  retryCount: number;
}

export class ErrorBoundary extends Component<Props, State> {
  private auditLogger = getAuditLogger();
  private static readonly MAX_RETRY_COUNT = 3;
  
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, retryCount: 0 };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    const errorId = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    return { 
      hasError: true, 
      error, 
      errorId,
      retryCount: 0
    };
  }

  async componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`Error caught by ErrorBoundary${this.props.name ? ` (${this.props.name})` : ''}:`, error, errorInfo);
    
    this.setState({ error, errorInfo });
    
    // SECURITY FIX: Enhanced error tracking and audit logging
    try {
      // Log to audit system
      await this.auditLogger.logSecurity(
        AuditEventType.SYSTEM_ERROR,
        `React Error Boundary caught error: ${error.message}`,
        {
          applicationName: 'DotMac Management Admin Portal',
          environment: process.env.NODE_ENV || 'development',
          resourceType: 'error_boundary',
          resourceName: this.props.name || 'UnnamedErrorBoundary'
        },
        {
          reason: 'react_error_boundary',
          customData: {
            errorMessage: error.message,
            errorName: error.name,
            componentStack: errorInfo.componentStack?.substring(0, 1000), // Limit size
            errorStack: error.stack?.substring(0, 2000), // Limit size
            errorId: this.state.errorId,
            retryCount: this.state.retryCount,
            timestamp: new Date().toISOString(),
            url: typeof window !== 'undefined' ? window.location.href : 'unknown',
            userAgent: typeof window !== 'undefined' ? navigator.userAgent : 'unknown'
          }
        }
      );
    } catch (auditError) {
      console.warn('Failed to log error to audit system:', auditError);
    }
    
    // Call custom error handler if provided
    if (this.props.onError) {
      try {
        this.props.onError(error, errorInfo);
      } catch (handlerError) {
        console.error('Error in custom error handler:', handlerError);
      }
    }
    
    // Send to monitoring service (production only)
    if (process.env.NODE_ENV === 'production') {
      this.reportToMonitoring(error, errorInfo);
    }
  }
  
  private async reportToMonitoring(error: Error, errorInfo: ErrorInfo) {
    try {
      await fetch('/api/monitoring/error', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          error: {
            message: error.message,
            name: error.name,
            stack: error.stack
          },
          errorInfo: {
            componentStack: errorInfo.componentStack
          },
          metadata: {
            errorId: this.state.errorId,
            componentName: this.props.name,
            retryCount: this.state.retryCount,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent
          }
        })
      });
    } catch (reportError) {
      console.warn('Failed to report error to monitoring service:', reportError);
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    const newRetryCount = this.state.retryCount + 1;
    
    // SECURITY FIX: Prevent infinite retry loops
    if (newRetryCount > ErrorBoundary.MAX_RETRY_COUNT) {
      console.warn(`Max retry count (${ErrorBoundary.MAX_RETRY_COUNT}) reached for error boundary`);
      return;
    }
    
    this.setState({ 
      hasError: false, 
      error: undefined, 
      errorInfo: undefined,
      retryCount: newRetryCount
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
          <div className="sm:mx-auto sm:w-full sm:max-w-md">
            <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
              <div className="text-center">
                <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-danger-400" />
                <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                  Something went wrong
                </h2>
                <p className="mt-2 text-center text-sm text-gray-600">
                  We apologize for the inconvenience. The application encountered an unexpected error.
                </p>

                {process.env.NODE_ENV === 'development' && this.state.error && (
                  <div className="mt-4 text-left">
                    <details className="bg-gray-50 p-4 rounded-md text-xs">
                      <summary className="cursor-pointer font-medium text-gray-700 mb-2">
                        Error Details
                      </summary>
                      <div className="space-y-2">
                        <div>
                          <strong>Error:</strong>
                          <pre className="mt-1 whitespace-pre-wrap text-red-600">
                            {this.state.error.message}
                          </pre>
                        </div>
                        
                        <div>
                          <strong>Stack Trace:</strong>
                          <pre className="mt-1 whitespace-pre-wrap text-gray-600 text-xs">
                            {this.state.error.stack}
                          </pre>
                        </div>

                        {this.state.errorInfo && (
                          <div>
                            <strong>Component Stack:</strong>
                            <pre className="mt-1 whitespace-pre-wrap text-gray-600 text-xs">
                              {this.state.errorInfo.componentStack}
                            </pre>
                          </div>
                        )}
                      </div>
                    </details>
                  </div>
                )}

                <div className="mt-6 space-y-3">
                  {this.state.retryCount < ErrorBoundary.MAX_RETRY_COUNT ? (
                    <button
                      onClick={this.handleReset}
                      className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    >
                      Try Again {this.state.retryCount > 0 && `(${this.state.retryCount}/${ErrorBoundary.MAX_RETRY_COUNT})`}
                    </button>
                  ) : (
                    <div className="text-center text-sm text-gray-500 p-2 bg-gray-100 rounded-md">
                      Maximum retry attempts reached. Please reload the page.
                    </div>
                  )}
                  
                  <button
                    onClick={this.handleReload}
                    className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                  >
                    Reload Page
                  </button>
                </div>

                <div className="mt-4 text-xs text-gray-500 space-y-2">
                  {this.state.errorId && (
                    <p>Error ID: <code className="bg-gray-100 px-2 py-1 rounded">{this.state.errorId}</code></p>
                  )}
                  <p>
                    If this problem persists, please contact support with the error ID and details above.
                  </p>
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