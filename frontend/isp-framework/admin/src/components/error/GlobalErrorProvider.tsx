/**
 * Global Error Provider - Application-wide error handling
 * Provides centralized error reporting and recovery mechanisms
 */

'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { ErrorBoundary } from './ErrorBoundary';

interface ErrorReport {
  id: string;
  timestamp: string;
  error: Error;
  context?: any;
  severity: 'low' | 'medium' | 'high' | 'critical';
  resolved?: boolean;
}

interface GlobalErrorContextType {
  errors: ErrorReport[];
  reportError: (error: Error, context?: any, severity?: ErrorReport['severity']) => string;
  resolveError: (id: string) => void;
  clearErrors: () => void;
  getUnresolvedErrors: () => ErrorReport[];
}

const GlobalErrorContext = createContext<GlobalErrorContextType | undefined>(undefined);

interface GlobalErrorProviderProps {
  children: ReactNode;
  maxErrors?: number;
  enableNotifications?: boolean;
}

export function GlobalErrorProvider({
  children,
  maxErrors = 50,
  enableNotifications = true,
}: GlobalErrorProviderProps) {
  const [errors, setErrors] = useState<ErrorReport[]>([]);

  const reportError = useCallback(
    (error: Error, context?: any, severity: ErrorReport['severity'] = 'medium'): string => {
      const id = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      const errorReport: ErrorReport = {
        id,
        timestamp: new Date().toISOString(),
        error,
        context,
        severity,
        resolved: false,
      };

      setErrors((prev) => {
        const newErrors = [errorReport, ...prev].slice(0, maxErrors);

        // Log critical errors immediately
        if (severity === 'critical') {
          console.error('🚨 CRITICAL ERROR:', error, context);
        }

        return newErrors;
      });

      // Show notification for high/critical errors
      if (enableNotifications && (severity === 'high' || severity === 'critical')) {
        showErrorNotification(errorReport);
      }

      return id;
    },
    [maxErrors, enableNotifications]
  );

  const resolveError = useCallback((id: string) => {
    setErrors((prev) =>
      prev.map((error) => (error.id === id ? { ...error, resolved: true } : error))
    );
  }, []);

  const clearErrors = useCallback(() => {
    setErrors([]);
  }, []);

  const getUnresolvedErrors = useCallback(() => {
    return errors.filter((error) => !error.resolved);
  }, [errors]);

  const contextValue: GlobalErrorContextType = {
    errors,
    reportError,
    resolveError,
    clearErrors,
    getUnresolvedErrors,
  };

  return (
    <GlobalErrorContext.Provider value={contextValue}>
      <ErrorBoundary
        level='page'
        onError={(error, errorInfo) => {
          reportError(error, { errorInfo }, 'critical');
        }}
      >
        {children}
      </ErrorBoundary>
    </GlobalErrorContext.Provider>
  );
}

export function useGlobalError() {
  const context = useContext(GlobalErrorContext);
  if (context === undefined) {
    throw new Error('useGlobalError must be used within a GlobalErrorProvider');
  }
  return context;
}

// Error notification system
function showErrorNotification(errorReport: ErrorReport) {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return;
  }

  // Request permission if not granted
  if (Notification.permission === 'default') {
    Notification.requestPermission();
  }

  if (Notification.permission === 'granted') {
    const notification = new Notification('Application Error', {
      body: `${errorReport.severity.toUpperCase()}: ${errorReport.error.message}`,
      icon: '/favicon.ico',
      tag: errorReport.id,
      requireInteraction: errorReport.severity === 'critical',
    });

    // Auto-close after 5 seconds for non-critical errors
    if (errorReport.severity !== 'critical') {
      setTimeout(() => notification.close(), 5000);
    }
  }
}

// Hook for async error handling
export function useAsyncError() {
  const { reportError } = useGlobalError();

  return useCallback(
    (error: Error, context?: any) => {
      reportError(error, context, 'high');
    },
    [reportError]
  );
}

// Hook for error recovery
export function useErrorRecovery() {
  const { resolveError } = useGlobalError();

  return {
    resolveError,
    withErrorRecovery: <T,>(operation: () => Promise<T>, fallback?: () => T, context?: any) => {
      return operation().catch((error) => {
        const { reportError } = useGlobalError();
        const errorId = reportError(error, context);

        if (fallback) {
          // Resolve immediately if we have a fallback
          resolveError(errorId);
          return fallback();
        }

        throw error;
      });
    },
  };
}

// Error status component
export function ErrorStatus() {
  const { getUnresolvedErrors, resolveError, clearErrors } = useGlobalError();
  const unresolvedErrors = getUnresolvedErrors();

  if (unresolvedErrors.length === 0) {
    return null;
  }

  const criticalErrors = unresolvedErrors.filter((e) => e.severity === 'critical');
  const highErrors = unresolvedErrors.filter((e) => e.severity === 'high');

  return (
    <div className='fixed bottom-4 right-4 space-y-2 z-50'>
      {criticalErrors.map((error) => (
        <div
          key={error.id}
          className='bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded shadow-lg max-w-sm'
        >
          <div className='flex justify-between items-start'>
            <div>
              <strong className='font-bold'>Critical Error</strong>
              <p className='text-sm'>{error.error.message}</p>
            </div>
            <button
              onClick={() => resolveError(error.id)}
              className='ml-2 text-red-500 hover:text-red-700'
            >
              ×
            </button>
          </div>
        </div>
      ))}

      {highErrors.length > 0 && (
        <div className='bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded shadow-lg max-w-sm'>
          <div className='flex justify-between items-center'>
            <span className='text-sm'>
              {highErrors.length} error{highErrors.length > 1 ? 's' : ''} occurred
            </span>
            <button
              onClick={clearErrors}
              className='ml-2 text-yellow-500 hover:text-yellow-700 text-sm underline'
            >
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
