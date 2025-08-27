/**
 * Comprehensive Error Boundary Component
 * Handles React errors with graceful fallbacks and recovery mechanisms
 */

'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug, ChevronDown, ChevronUp } from 'lucide-react';
import { env } from '@/lib/env-config';

// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

interface CustomErrorInfo {
  componentStack: string;
  errorBoundary?: string;
  errorBoundaryStack?: string;
  timestamp?: string;
  userAgent?: string;
  url?: string;
  boundaryName?: string;
  boundaryLevel?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: CustomErrorInfo | null;
  errorId: string;
  retryCount: number;
  showDetails: boolean;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: CustomErrorInfo, errorId: string) => void;
  maxRetries?: number;
  isolate?: boolean;
  level?: 'page' | 'section' | 'component';
  name?: string;
}

interface ErrorFallbackProps {
  error: Error;
  errorInfo: CustomErrorInfo;
  errorId: string;
  retry: () => void;
  retryCount: number;
  maxRetries: number;
  goHome: () => void;
  reportError: () => void;
  level: string;
  name?: string;
}

// ============================================================================
// ERROR BOUNDARY COMPONENT
// ============================================================================

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private retryTimeoutId: NodeJS.Timeout | null = null;
  
  constructor(props: ErrorBoundaryProps) {
    super(props);
    
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
      retryCount: 0,
      showDetails: false,
    };
  }
  
  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    const errorId = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    return {
      hasError: true,
      error,
      errorId,
      showDetails: false,
    };
  }
  
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { onError, name } = this.props;
    const { errorId } = this.state;
    
    // Enhanced error info
    const enhancedErrorInfo: CustomErrorInfo = {
      componentStack: errorInfo.componentStack,
      errorBoundary: errorInfo.errorBoundary,
      errorBoundaryStack: errorInfo.errorBoundaryStack,
      timestamp: new Date().toISOString(),
      userAgent: typeof window !== 'undefined' ? window.navigator.userAgent : 'unknown',
      url: typeof window !== 'undefined' ? window.location.href : 'unknown',
      boundaryName: name || 'Unknown',
      boundaryLevel: this.props.level || 'component',
    };
    
    this.setState({ errorInfo: enhancedErrorInfo });
    
    // Log error
    console.error('Error Boundary caught an error:', {
      error,
      errorInfo: enhancedErrorInfo,
      errorId,
    });
    
    // Call custom error handler
    if (onError) {
      onError(error, enhancedErrorInfo, errorId);
    }
    
    // Send to error reporting service in production
    if (env.NODE_ENV === 'production') {
      this.reportToService(error, enhancedErrorInfo, errorId);
    }
  }
  
  componentWillUnmount() {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }
  
  private reportToService = async (error: Error, errorInfo: any, errorId: string) => {
    try {
      // TODO: Integrate with error reporting service (Sentry, LogRocket, etc.)
      const errorReport = {
        errorId,
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        userAgent: errorInfo.userAgent,
        url: errorInfo.url,
        timestamp: errorInfo.timestamp,
        boundaryName: errorInfo.boundaryName,
        boundaryLevel: errorInfo.boundaryLevel,
        retryCount: this.state.retryCount,
      };
      
      if (env.SENTRY_DSN) {
        // await Sentry.captureException(error, {
        //   tags: { errorBoundary: errorInfo.boundaryName },
        //   extra: errorReport,
        // });
      }
      
      // Send to custom webhook if configured
      if (process.env.ERROR_WEBHOOK_URL) {
        await fetch(process.env.ERROR_WEBHOOK_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'error_boundary',
            data: errorReport,
          }),
        });
      }
    } catch (reportingError) {
      console.error('Failed to report error:', reportingError);
    }
  };
  
  private handleRetry = () => {
    const { maxRetries = 3 } = this.props;
    const { retryCount } = this.state;
    
    if (retryCount >= maxRetries) {
      console.warn('Maximum retry attempts reached');
      return;
    }
    
    console.log(`Retrying... Attempt ${retryCount + 1}/${maxRetries}`);
    
    // Add delay before retry to prevent rapid failing
    const delay = Math.min(1000 * Math.pow(2, retryCount), 5000); // Exponential backoff
    
    this.retryTimeoutId = setTimeout(() => {
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        retryCount: retryCount + 1,
        showDetails: false,
      });
    }, delay);
  };
  
  private handleGoHome = () => {
    if (typeof window !== 'undefined') {
      window.location.href = '/dashboard';
    }
  };
  
  private handleReportError = () => {
    const { error, errorInfo, errorId } = this.state;
    
    if (error && errorInfo) {
      // Create mailto link with error details
      const subject = encodeURIComponent(`Error Report: ${error.message}`);
      const body = encodeURIComponent(
        `Error ID: ${errorId}\n\n` +
        `Error Message: ${error.message}\n\n` +
        `Component Stack:\n${errorInfo.componentStack}\n\n` +
        `Error Stack:\n${error.stack}\n\n` +
        `URL: ${typeof window !== 'undefined' ? window.location.href : 'unknown'}\n` +
        `Timestamp: ${new Date().toISOString()}\n` +
        `User Agent: ${typeof window !== 'undefined' ? window.navigator.userAgent : 'unknown'}`
      );
      
      const mailtoLink = `mailto:${'support@dotmac.cloud'}?subject=${subject}&body=${body}`;
      window.open(mailtoLink);
    }
  };
  
  private toggleDetails = () => {
    this.setState(prevState => ({
      showDetails: !prevState.showDetails,
    }));
  };
  
  render() {
    const { hasError, error, errorInfo, errorId, retryCount, showDetails } = this.state;
    const { children, fallback: FallbackComponent, maxRetries = 3, level = 'component', name } = this.props;
    
    if (hasError && error) {
      // Use custom fallback if provided
      if (FallbackComponent) {
        return (
          <FallbackComponent
            error={error}
            errorInfo={errorInfo!}
            errorId={errorId}
            retry={this.handleRetry}
            retryCount={retryCount}
            maxRetries={maxRetries}
            goHome={this.handleGoHome}
            reportError={this.handleReportError}
            level={level}
            name={name}
          />
        );
      }
      
      // Default fallback UI
      return <DefaultErrorFallback
        error={error}
        errorInfo={errorInfo!}
        errorId={errorId}
        retry={this.handleRetry}
        retryCount={retryCount}
        maxRetries={maxRetries}
        goHome={this.handleGoHome}
        reportError={this.handleReportError}
        level={level}
        name={name}
        showDetails={showDetails}
        toggleDetails={this.toggleDetails}
      />;
    }
    
    return children;
  }
}

// ============================================================================
// DEFAULT ERROR FALLBACK COMPONENT
// ============================================================================

interface DefaultErrorFallbackProps extends ErrorFallbackProps {
  showDetails: boolean;
  toggleDetails: () => void;
}

const DefaultErrorFallback: React.FC<DefaultErrorFallbackProps> = ({
  error,
  errorInfo,
  errorId,
  retry,
  retryCount,
  maxRetries,
  goHome,
  reportError,
  level,
  name,
  showDetails,
  toggleDetails,
}) => {
  const canRetry = retryCount < maxRetries;
  const isPageLevel = level === 'page';
  
  const getLevelStyles = () => {
    switch (level) {
      case 'page':
        return 'min-h-screen bg-gray-50 flex items-center justify-center p-4';
      case 'section':
        return 'min-h-64 bg-gray-50 flex items-center justify-center p-6 rounded-lg border';
      default:
        return 'bg-red-50 border border-red-200 rounded-lg p-4';
    }
  };
  
  const getErrorIcon = () => {
    const iconClass = isPageLevel ? 'h-16 w-16' : 'h-8 w-8';
    const colorClass = 'text-red-500';
    
    return <AlertTriangle className={`${iconClass} ${colorClass} mb-4`} />;
  };
  
  const getTitle = () => {
    if (isPageLevel) return 'Oops! Something went wrong';
    if (level === 'section') return 'Section Error';
    return name ? `${name} Error` : 'Component Error';
  };
  
  const getDescription = () => {
    if (isPageLevel) {
      return "We're sorry for the inconvenience. The page encountered an unexpected error.";
    }
    return `This ${level} encountered an error and couldn't render properly.`;
  };
  
  return (
    <div className={getLevelStyles()}>
      <div className={`max-w-md text-center ${isPageLevel ? '' : 'w-full'}`}>
        {getErrorIcon()}
        
        <h1 className={`${isPageLevel ? 'text-2xl' : 'text-lg'} font-bold text-gray-900 mb-2`}>
          {getTitle()}
        </h1>
        
        <p className="text-gray-600 mb-6">
          {getDescription()}
        </p>
        
        {/* Error ID */}
        <div className="mb-4 p-3 bg-gray-100 rounded-md">
          <p className="text-sm text-gray-600">
            Error ID: <span className="font-mono font-medium">{errorId}</span>
          </p>
          {retryCount > 0 && (
            <p className="text-sm text-gray-500 mt-1">
              Retry attempts: {retryCount}/{maxRetries}
            </p>
          )}
        </div>
        
        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-4">
          {canRetry && (
            <button
              onClick={retry}
              className="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </button>
          )}
          
          {isPageLevel && (
            <button
              onClick={goHome}
              className="flex items-center justify-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              <Home className="h-4 w-4 mr-2" />
              Go to Dashboard
            </button>
          )}
          
          <button
            onClick={reportError}
            className="flex items-center justify-center px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
          >
            <Bug className="h-4 w-4 mr-2" />
            Report Issue
          </button>
        </div>
        
        {/* Error details toggle */}
        {env.DEBUG && (
          <div>
            <button
              onClick={toggleDetails}
              className="flex items-center text-sm text-gray-500 hover:text-gray-700 mx-auto mb-2"
            >
              Technical Details
              {showDetails ? (
                <ChevronUp className="h-4 w-4 ml-1" />
              ) : (
                <ChevronDown className="h-4 w-4 ml-1" />
              )}
            </button>
            
            {showDetails && (
              <div className="text-left bg-gray-100 rounded-md p-3 mt-2">
                <div className="mb-3">
                  <strong className="text-sm text-gray-700">Error Message:</strong>
                  <pre className="text-xs text-red-600 mt-1 whitespace-pre-wrap break-words">
                    {error.message}
                  </pre>
                </div>
                
                <div className="mb-3">
                  <strong className="text-sm text-gray-700">Component Stack:</strong>
                  <pre className="text-xs text-gray-600 mt-1 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
                    {errorInfo?.componentStack}
                  </pre>
                </div>
                
                {error.stack && (
                  <div>
                    <strong className="text-sm text-gray-700">Stack Trace:</strong>
                    <pre className="text-xs text-gray-600 mt-1 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
                      {error.stack}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// SPECIALIZED ERROR BOUNDARIES
// ============================================================================

// Page-level error boundary
export const PageErrorBoundary: React.FC<Omit<ErrorBoundaryProps, 'level'>> = (props) => (
  <ErrorBoundary {...props} level="page" />
);

// Section-level error boundary
export const SectionErrorBoundary: React.FC<Omit<ErrorBoundaryProps, 'level'>> = (props) => (
  <ErrorBoundary {...props} level="section" />
);

// Component-level error boundary
export const ComponentErrorBoundary: React.FC<Omit<ErrorBoundaryProps, 'level'>> = (props) => (
  <ErrorBoundary {...props} level="component" />
);

// ============================================================================
// ERROR BOUNDARY HOC
// ============================================================================

export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const WrappedComponent = React.forwardRef<any, P>((props, ref) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props as P} ref={ref} />
    </ErrorBoundary>
  ));
  
  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}

// ============================================================================
// ERROR BOUNDARY HOOK
// ============================================================================

export function useErrorHandler() {
  return React.useCallback((error: Error, errorInfo?: any) => {
    // This would typically be handled by the nearest error boundary
    // For unhandled promise rejections or other async errors
    console.error('Unhandled error:', error, errorInfo);
    
    // You can also manually throw to trigger error boundary
    throw error;
  }, []);
}

// ============================================================================
// EXPORT DEFAULT
// ============================================================================

export default ErrorBoundary;