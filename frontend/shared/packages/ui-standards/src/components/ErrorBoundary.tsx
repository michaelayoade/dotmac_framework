import React from 'react';
import { ErrorBoundary as ReactErrorBoundary, FallbackProps } from 'react-error-boundary';
import { ErrorShell, ServerErrorShell } from './ErrorShell';

interface ErrorInfo {
  componentStack: string;
  errorBoundary?: string;
  errorBoundaryStack?: string;
}

interface StandardErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<FallbackProps>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  onReset?: () => void;
  resetKeys?: Array<string | number>;
  isolate?: boolean;
  level?: 'page' | 'section' | 'component';
}

const DefaultErrorFallback: React.FC<FallbackProps> = ({ error, resetErrorBoundary }) => {
  return (
    <ErrorShell
      title="Something went wrong"
      message="An error occurred in this component"
      error={error}
      onRetry={resetErrorBoundary}
      variant="destructive"
    />
  );
};

const PageErrorFallback: React.FC<FallbackProps> = ({ error, resetErrorBoundary }) => {
  return (
    <ServerErrorShell
      onRetry={resetErrorBoundary}
      onHome={() => window.location.href = '/'}
    />
  );
};

const SectionErrorFallback: React.FC<FallbackProps> = ({ error, resetErrorBoundary }) => {
  return (
    <ErrorShell
      title="Section Error"
      message="This section encountered an error"
      error={error}
      onRetry={resetErrorBoundary}
      variant="warning"
      size="sm"
    />
  );
};

const ComponentErrorFallback: React.FC<FallbackProps> = ({ error, resetErrorBoundary }) => {
  return (
    <div className="border border-red-200 bg-red-50 rounded p-3 text-center">
      <p className="text-sm text-red-700">Component failed to load</p>
      <button
        onClick={resetErrorBoundary}
        className="mt-2 text-xs text-red-800 underline hover:no-underline"
      >
        Retry
      </button>
    </div>
  );
};

export const StandardErrorBoundary: React.FC<StandardErrorBoundaryProps> = ({
  children,
  fallback,
  onError,
  onReset,
  resetKeys,
  isolate = false,
  level = 'component',
}) => {
  const getFallbackComponent = () => {
    if (fallback) return fallback;
    
    switch (level) {
      case 'page':
        return PageErrorFallback;
      case 'section':
        return SectionErrorFallback;
      case 'component':
      default:
        return ComponentErrorFallback;
    }
  };

  const handleError = (error: Error, errorInfo: ErrorInfo) => {
    // Log to error reporting service
    console.error('ErrorBoundary caught an error:', error);
    console.error('Component stack:', errorInfo.componentStack);
    
    // Report to external service
    if (typeof window !== 'undefined') {
      // Example: Sentry, LogRocket, etc.
      window.dispatchEvent(new CustomEvent('error:boundary', {
        detail: {
          error: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          level,
          timestamp: new Date().toISOString(),
        }
      }));
    }

    onError?.(error, errorInfo);
  };

  return (
    <ReactErrorBoundary
      FallbackComponent={getFallbackComponent()}
      onError={handleError}
      onReset={onReset}
      resetKeys={resetKeys}
      isolate={isolate}
    >
      {children}
    </ReactErrorBoundary>
  );
};

// Convenience components for different levels
export const PageErrorBoundary: React.FC<{
  children: React.ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}> = ({ children, onError }) => {
  return (
    <StandardErrorBoundary level="page" onError={onError}>
      {children}
    </StandardErrorBoundary>
  );
};

export const SectionErrorBoundary: React.FC<{
  children: React.ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  resetKeys?: Array<string | number>;
}> = ({ children, onError, resetKeys }) => {
  return (
    <StandardErrorBoundary level="section" onError={onError} resetKeys={resetKeys}>
      {children}
    </StandardErrorBoundary>
  );
};

export const ComponentErrorBoundary: React.FC<{
  children: React.ReactNode;
  fallback?: React.ComponentType<FallbackProps>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}> = ({ children, fallback, onError }) => {
  return (
    <StandardErrorBoundary 
      level="component" 
      fallback={fallback} 
      onError={onError}
      isolate
    >
      {children}
    </StandardErrorBoundary>
  );
};

// HOC for wrapping components with error boundaries
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<StandardErrorBoundaryProps, 'children'>
) {
  const WrappedComponent: React.FC<P> = (props) => {
    return (
      <StandardErrorBoundary {...errorBoundaryProps}>
        <Component {...props} />
      </StandardErrorBoundary>
    );
  };

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}