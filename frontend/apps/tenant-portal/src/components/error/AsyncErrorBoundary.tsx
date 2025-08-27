/**
 * Async Error Boundary Component
 * Handles asynchronous errors and promise rejections
 */

'use client';

import React, { Component, ReactNode } from 'react';
import { ErrorBoundary } from './ErrorBoundary';

// ============================================================================
// ASYNC ERROR STATE MANAGEMENT
// ============================================================================

interface AsyncErrorState {
  asyncError: Error | null;
}

interface AsyncErrorBoundaryProps {
  children: ReactNode;
  fallback?: React.ComponentType<any>;
  onAsyncError?: (error: Error) => void;
}

// ============================================================================
// ASYNC ERROR BOUNDARY COMPONENT
// ============================================================================

export class AsyncErrorBoundary extends Component<AsyncErrorBoundaryProps, AsyncErrorState> {
  constructor(props: AsyncErrorBoundaryProps) {
    super(props);
    
    this.state = {
      asyncError: null,
    };
  }
  
  componentDidMount() {
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', this.handleUnhandledRejection);
    
    // Handle general errors
    window.addEventListener('error', this.handleError);
  }
  
  componentWillUnmount() {
    window.removeEventListener('unhandledrejection', this.handleUnhandledRejection);
    window.removeEventListener('error', this.handleError);
  }
  
  handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    const error = event.reason instanceof Error 
      ? event.reason 
      : new Error(String(event.reason));
    
    console.error('Unhandled promise rejection:', error);
    
    // Call custom error handler
    if (this.props.onAsyncError) {
      this.props.onAsyncError(error);
    }
    
    // Set async error state to trigger error boundary
    this.setState({ asyncError: error });
    
    // Prevent the error from being logged to console again
    event.preventDefault();
  };
  
  handleError = (event: ErrorEvent) => {
    const error = event.error instanceof Error 
      ? event.error 
      : new Error(event.message);
    
    console.error('Unhandled error:', error);
    
    // Call custom error handler
    if (this.props.onAsyncError) {
      this.props.onAsyncError(error);
    }
    
    // Set async error state
    this.setState({ asyncError: error });
  };
  
  static getDerivedStateFromError(error: Error): AsyncErrorState {
    return { asyncError: error };
  }
  
  render() {
    const { asyncError } = this.state;
    const { children, fallback } = this.props;
    
    if (asyncError) {
      // Throw the error to be caught by the parent ErrorBoundary
      throw asyncError;
    }
    
    return children;
  }
}

// ============================================================================
// ASYNC ERROR BOUNDARY WITH ERROR BOUNDARY WRAPPER
// ============================================================================

export const AsyncErrorBoundaryWrapper: React.FC<AsyncErrorBoundaryProps & {
  level?: 'page' | 'section' | 'component';
  name?: string;
}> = ({ children, level, name, ...props }) => {
  return (
    <ErrorBoundary level={level} name={name}>
      <AsyncErrorBoundary {...props}>
        {children}
      </AsyncErrorBoundary>
    </ErrorBoundary>
  );
};

// ============================================================================
// ASYNC ERROR HANDLER HOOK
// ============================================================================

export function useAsyncError() {
  const [, forceUpdate] = React.useReducer((x: number) => x + 1, 0);
  
  return React.useCallback((error: Error) => {
    // Force component to re-render and throw the error
    // This will be caught by the nearest error boundary
    forceUpdate();
    throw error;
  }, [forceUpdate]);
}

// ============================================================================
// SAFE ASYNC OPERATIONS
// ============================================================================

/**
 * Safe async function wrapper that catches errors and reports them
 */
export function safeAsync<T extends any[], R>(
  asyncFn: (...args: T) => Promise<R>,
  onError?: (error: Error) => void
) {
  return async (...args: T): Promise<R | null> => {
    try {
      return await asyncFn(...args);
    } catch (error) {
      const errorObj = error instanceof Error ? error : new Error(String(error));
      
      if (onError) {
        onError(errorObj);
      } else {
        console.error('Async error:', errorObj);
      }
      
      return null;
    }
  };
}

/**
 * Safe promise wrapper
 */
export function safePromise<T>(
  promise: Promise<T>,
  onError?: (error: Error) => void
): Promise<T | null> {
  return promise.catch((error) => {
    const errorObj = error instanceof Error ? error : new Error(String(error));
    
    if (onError) {
      onError(errorObj);
    } else {
      console.error('Promise error:', errorObj);
    }
    
    return null;
  });
}

// ============================================================================
// ASYNC COMPONENT WRAPPER
// ============================================================================

interface AsyncComponentProps {
  children: ReactNode;
  loading?: ReactNode;
  error?: ReactNode;
  onError?: (error: Error) => void;
}

interface AsyncComponentState {
  isLoading: boolean;
  error: Error | null;
}

export class AsyncComponent extends Component<AsyncComponentProps, AsyncComponentState> {
  private mounted = true;
  
  constructor(props: AsyncComponentProps) {
    super(props);
    
    this.state = {
      isLoading: true,
      error: null,
    };
  }
  
  componentDidMount() {
    this.mounted = true;
    
    // Simulate async operation completion
    setTimeout(() => {
      if (this.mounted) {
        this.setState({ isLoading: false });
      }
    }, 100);
  }
  
  componentWillUnmount() {
    this.mounted = false;
  }
  
  componentDidCatch(error: Error) {
    if (this.mounted) {
      this.setState({ error });
      
      if (this.props.onError) {
        this.props.onError(error);
      }
    }
  }
  
  render() {
    const { children, loading, error: errorFallback } = this.props;
    const { isLoading, error } = this.state;
    
    if (error) {
      return errorFallback || (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">Failed to load component</p>
        </div>
      );
    }
    
    if (isLoading) {
      return loading || (
        <div className="p-4">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      );
    }
    
    return children;
  }
}

// ============================================================================
// EXPORTS
// ============================================================================

export default AsyncErrorBoundaryWrapper;