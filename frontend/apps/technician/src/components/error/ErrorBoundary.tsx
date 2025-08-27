/**
 * Global Error Boundary and Error Handling System
 * Provides comprehensive error handling, recovery, and user feedback
 */

'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  RefreshCw,
  Home,
  Bug,
  Wifi,
  WifiOff,
  Database,
  Camera,
  MapPin,
  Smartphone,
} from 'lucide-react';

// Error types for better categorization
export enum ErrorType {
  NETWORK = 'NETWORK',
  DATABASE = 'DATABASE',
  AUTHENTICATION = 'AUTHENTICATION',
  PERMISSION = 'PERMISSION',
  VALIDATION = 'VALIDATION',
  CAMERA = 'CAMERA',
  GEOLOCATION = 'GEOLOCATION',
  STORAGE = 'STORAGE',
  SYNC = 'SYNC',
  GENERIC = 'GENERIC',
}

export interface AppError {
  type: ErrorType;
  message: string;
  code?: string;
  originalError?: Error;
  timestamp: string;
  userAgent: string;
  url: string;
  userId?: string;
  context?: Record<string, any>;
  recoverable: boolean;
  retryable: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: AppError | null;
  errorId: string | null;
  retryCount: number;
  isRetrying: boolean;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: AppError, retry: () => void) => ReactNode;
  onError?: (error: AppError, errorInfo: ErrorInfo) => void;
  showDetails?: boolean;
}

// Error logging service
class ErrorLogger {
  private static instance: ErrorLogger;
  private errors: AppError[] = [];
  private maxErrors = 100;

  static getInstance(): ErrorLogger {
    if (!ErrorLogger.instance) {
      ErrorLogger.instance = new ErrorLogger();
    }
    return ErrorLogger.instance;
  }

  log(error: AppError): void {
    // Add to local storage
    this.errors.unshift(error);
    if (this.errors.length > this.maxErrors) {
      this.errors = this.errors.slice(0, this.maxErrors);
    }

    // Store in localStorage for persistence
    try {
      localStorage.setItem('technician_errors', JSON.stringify(this.errors.slice(0, 10)));
    } catch (e) {
      console.warn('Failed to store error in localStorage:', e);
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('App Error:', error);
    }

    // Send to monitoring service (if online)
    this.sendToMonitoring(error);
  }

  private async sendToMonitoring(error: AppError): Promise<void> {
    if (!navigator.onLine) return;

    try {
      await fetch('/api/v1/monitoring/errors', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(error),
      });
    } catch (e) {
      console.warn('Failed to send error to monitoring service:', e);
    }
  }

  getErrors(): AppError[] {
    return [...this.errors];
  }

  clearErrors(): void {
    this.errors = [];
    try {
      localStorage.removeItem('technician_errors');
    } catch (e) {
      console.warn('Failed to clear errors from localStorage:', e);
    }
  }
}

// Error utilities
export function createAppError(
  type: ErrorType,
  message: string,
  originalError?: Error,
  context?: Record<string, any>
): AppError {
  return {
    type,
    message,
    code: originalError?.name,
    originalError,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    url: window.location.href,
    context,
    recoverable: isRecoverable(type),
    retryable: isRetryable(type),
  };
}

function isRecoverable(type: ErrorType): boolean {
  return [
    ErrorType.NETWORK,
    ErrorType.DATABASE,
    ErrorType.PERMISSION,
    ErrorType.CAMERA,
    ErrorType.GEOLOCATION,
    ErrorType.SYNC,
  ].includes(type);
}

function isRetryable(type: ErrorType): boolean {
  return [
    ErrorType.NETWORK,
    ErrorType.DATABASE,
    ErrorType.CAMERA,
    ErrorType.GEOLOCATION,
    ErrorType.SYNC,
  ].includes(type);
}

// Error boundary component
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private logger = ErrorLogger.getInstance();
  private retryTimeout: NodeJS.Timeout | null = null;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorId: null,
      retryCount: 0,
      isRetrying: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    const appError = createAppError(
      ErrorType.GENERIC,
      'An unexpected error occurred',
      error
    );

    return {
      hasError: true,
      error: appError,
      errorId: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const appError = createAppError(
      this.categorizeError(error),
      error.message,
      error,
      { errorInfo }
    );

    this.logger.log(appError);
    this.props.onError?.(appError, errorInfo);
  }

  private categorizeError(error: Error): ErrorType {
    const message = error.message.toLowerCase();
    const stack = error.stack?.toLowerCase() || '';

    if (message.includes('network') || message.includes('fetch')) {
      return ErrorType.NETWORK;
    }
    if (message.includes('database') || message.includes('idb')) {
      return ErrorType.DATABASE;
    }
    if (message.includes('auth') || message.includes('unauthorized')) {
      return ErrorType.AUTHENTICATION;
    }
    if (message.includes('permission') || message.includes('denied')) {
      return ErrorType.PERMISSION;
    }
    if (message.includes('camera') || message.includes('getusermedia')) {
      return ErrorType.CAMERA;
    }
    if (message.includes('geolocation') || message.includes('position')) {
      return ErrorType.GEOLOCATION;
    }
    if (message.includes('storage') || message.includes('quota')) {
      return ErrorType.STORAGE;
    }
    if (message.includes('sync') || stack.includes('sync')) {
      return ErrorType.SYNC;
    }

    return ErrorType.GENERIC;
  }

  private handleRetry = () => {
    const { error, retryCount } = this.state;
    
    if (!error || !error.retryable || retryCount >= 3) {
      return;
    }

    this.setState({ isRetrying: true });

    // Exponential backoff
    const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);
    
    this.retryTimeout = setTimeout(() => {
      this.setState({
        hasError: false,
        error: null,
        errorId: null,
        retryCount: retryCount + 1,
        isRetrying: false,
      });
    }, delay);
  };

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorId: null,
      retryCount: 0,
      isRetrying: false,
    });
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  componentWillUnmount() {
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
    }
  }

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleRetry);
      }

      return (
        <ErrorFallbackUI
          error={this.state.error}
          errorId={this.state.errorId!}
          retryCount={this.state.retryCount}
          isRetrying={this.state.isRetrying}
          onRetry={this.handleRetry}
          onReset={this.handleReset}
          onGoHome={this.handleGoHome}
          showDetails={this.props.showDetails}
        />
      );
    }

    return this.props.children;
  }
}

// Error fallback UI component
interface ErrorFallbackUIProps {
  error: AppError;
  errorId: string;
  retryCount: number;
  isRetrying: boolean;
  onRetry: () => void;
  onReset: () => void;
  onGoHome: () => void;
  showDetails?: boolean;
}

function ErrorFallbackUI({
  error,
  errorId,
  retryCount,
  isRetrying,
  onRetry,
  onReset,
  onGoHome,
  showDetails = false,
}: ErrorFallbackUIProps) {
  const getErrorIcon = (type: ErrorType) => {
    switch (type) {
      case ErrorType.NETWORK:
        return <WifiOff className="w-12 h-12 text-red-500" />;
      case ErrorType.DATABASE:
        return <Database className="w-12 h-12 text-red-500" />;
      case ErrorType.CAMERA:
        return <Camera className="w-12 h-12 text-red-500" />;
      case ErrorType.GEOLOCATION:
        return <MapPin className="w-12 h-12 text-red-500" />;
      case ErrorType.PERMISSION:
        return <Smartphone className="w-12 h-12 text-red-500" />;
      default:
        return <AlertTriangle className="w-12 h-12 text-red-500" />;
    }
  };

  const getErrorTitle = (type: ErrorType) => {
    switch (type) {
      case ErrorType.NETWORK:
        return 'Connection Problem';
      case ErrorType.DATABASE:
        return 'Data Storage Issue';
      case ErrorType.AUTHENTICATION:
        return 'Authentication Required';
      case ErrorType.PERMISSION:
        return 'Permission Required';
      case ErrorType.CAMERA:
        return 'Camera Access Issue';
      case ErrorType.GEOLOCATION:
        return 'Location Access Issue';
      case ErrorType.STORAGE:
        return 'Storage Issue';
      case ErrorType.SYNC:
        return 'Sync Problem';
      default:
        return 'Something went wrong';
    }
  };

  const getErrorDescription = (type: ErrorType) => {
    switch (type) {
      case ErrorType.NETWORK:
        return 'Please check your internet connection and try again.';
      case ErrorType.DATABASE:
        return 'There was a problem accessing your data. This may be temporary.';
      case ErrorType.AUTHENTICATION:
        return 'Your session has expired. Please sign in again.';
      case ErrorType.PERMISSION:
        return 'This feature needs permission to work properly.';
      case ErrorType.CAMERA:
        return 'Camera access is required for this feature.';
      case ErrorType.GEOLOCATION:
        return 'Location access is needed for field operations.';
      case ErrorType.STORAGE:
        return 'Device storage is full or unavailable.';
      case ErrorType.SYNC:
        return 'Data synchronization failed. Changes are saved locally.';
      default:
        return 'An unexpected error occurred. Please try again.';
    }
  };

  const canRetry = error.retryable && retryCount < 3;

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md w-full"
      >
        <div className="bg-white rounded-lg shadow-lg p-6 text-center">
          {/* Error Icon */}
          <div className="mb-6">
            {getErrorIcon(error.type)}
          </div>

          {/* Error Title */}
          <h1 className="text-xl font-bold text-gray-900 mb-2">
            {getErrorTitle(error.type)}
          </h1>

          {/* Error Description */}
          <p className="text-gray-600 mb-6">
            {getErrorDescription(error.type)}
          </p>

          {/* Error Details */}
          {showDetails && (
            <div className="bg-gray-50 rounded-lg p-4 mb-6 text-left">
              <h3 className="font-medium text-gray-900 mb-2">Technical Details</h3>
              <div className="text-sm text-gray-600 space-y-1">
                <div><strong>Error ID:</strong> {errorId}</div>
                <div><strong>Type:</strong> {error.type}</div>
                <div><strong>Message:</strong> {error.message}</div>
                <div><strong>Time:</strong> {new Date(error.timestamp).toLocaleString()}</div>
                {retryCount > 0 && (
                  <div><strong>Retry Attempts:</strong> {retryCount}</div>
                )}
              </div>
            </div>
          )}

          {/* Retry Status */}
          <AnimatePresence>
            {isRetrying && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="mb-4"
              >
                <div className="flex items-center justify-center text-blue-600">
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  <span>Retrying...</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Action Buttons */}
          <div className="space-y-3">
            {/* Retry Button */}
            {canRetry && !isRetrying && (
              <button
                onClick={onRetry}
                className="w-full bg-primary-600 hover:bg-primary-700 text-white py-3 px-4 rounded-lg font-medium flex items-center justify-center transition-colors"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
              </button>
            )}

            {/* Reset Button */}
            {error.recoverable && (
              <button
                onClick={onReset}
                className="w-full bg-gray-600 hover:bg-gray-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
              >
                Reset
              </button>
            )}

            {/* Home Button */}
            <button
              onClick={onGoHome}
              className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 py-3 px-4 rounded-lg font-medium flex items-center justify-center transition-colors"
            >
              <Home className="w-4 h-4 mr-2" />
              Go to Dashboard
            </button>
          </div>

          {/* Offline Indicator */}
          {!navigator.onLine && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center text-yellow-800 text-sm">
                <WifiOff className="w-4 h-4 mr-2" />
                You're currently offline. Some features may not work.
              </div>
            </div>
          )}

          {/* Help Text */}
          <div className="mt-4 text-xs text-gray-500">
            Error ID: {errorId}
            <br />
            If this problem persists, please contact support.
          </div>
        </div>
      </motion.div>
    </div>
  );
}

// Toast notification component for non-critical errors
export function ErrorToast({ 
  error, 
  onDismiss 
}: { 
  error: AppError; 
  onDismiss: () => void;
}) {
  React.useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <motion.div
      initial={{ opacity: 0, y: -50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -50 }}
      className="fixed top-4 left-4 right-4 z-50 max-w-md mx-auto"
    >
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg">
        <div className="flex items-start">
          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" />
          <div className="flex-1">
            <h4 className="font-medium text-red-800 text-sm">
              {getErrorTitle(error.type)}
            </h4>
            <p className="text-red-700 text-sm mt-1">{error.message}</p>
          </div>
          <button
            onClick={onDismiss}
            className="ml-2 text-red-500 hover:text-red-700"
          >
            ×
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// Export error utilities
export { ErrorLogger, createAppError };
export default ErrorBoundary;