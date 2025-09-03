/**
 * Production-ready Sentry Error Boundary
 * Provides comprehensive error handling with user feedback and recovery options
 */

import React, { Component, type ReactNode } from 'react';
import * as Sentry from '@sentry/nextjs';
import type { PortalType, ErrorSeverity } from './types';

interface ErrorBoundaryProps {
  children: ReactNode;
  portalType: PortalType;
  fallback?: (error: Error, eventId: string) => ReactNode;
  showDialog?: boolean;
  enableReporting?: boolean;
  level?: ErrorSeverity;
  tags?: Record<string, string>;
  beforeCapture?: (error: Error) => void;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  eventId: string | null;
  errorInfo: React.ErrorInfo | null;
}

export class SentryErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      eventId: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const {
      portalType,
      beforeCapture,
      onError,
      enableReporting = true,
      level = 'error',
      tags,
    } = this.props;

    // Execute custom error handler if provided
    if (onError) {
      onError(error, errorInfo);
    }

    // Execute pre-capture logic if provided
    if (beforeCapture) {
      beforeCapture(error);
    }

    let eventId: string | null = null;

    if (enableReporting) {
      // Capture the error with Sentry
      eventId = Sentry.captureException(error, {
        level,
        tags: {
          portal: portalType,
          errorBoundary: true,
          component: errorInfo.componentStack.split('\n')[1]?.trim() || 'unknown',
          ...tags,
        },
        extra: {
          componentStack: errorInfo.componentStack,
          errorBoundary: 'SentryErrorBoundary',
        },
        contexts: {
          react: {
            componentStack: errorInfo.componentStack,
          },
        },
      });
    }

    this.setState({
      eventId,
      errorInfo,
    });

    // Show user feedback dialog if enabled
    if (this.props.showDialog && eventId) {
      this.showUserFeedbackDialog(eventId);
    }
  }

  private showUserFeedbackDialog = (eventId: string) => {
    Sentry.showReportDialog({
      eventId,
      title: 'Something went wrong',
      subtitle:
        'Our team has been notified. You can help us improve by providing additional details.',
      subtitle2: 'If you continue to experience issues, please contact support.',
      labelName: 'Name',
      labelEmail: 'Email',
      labelComments: 'What happened?',
      labelClose: 'Close',
      labelSubmit: 'Submit Report',
      errorGeneric: 'An error occurred while submitting your report. Please try again.',
      errorFormEntry: 'Some fields were invalid. Please check and try again.',
      successMessage: 'Thank you for the report!',
    });
  };

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      eventId: null,
      errorInfo: null,
    });
  };

  private handleReportBug = () => {
    if (this.state.eventId) {
      this.showUserFeedbackDialog(this.state.eventId);
    }
  };

  render() {
    if (this.state.hasError && this.state.error) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.state.eventId || '');
      }

      // Default error UI
      return (
        <DefaultErrorFallback
          error={this.state.error}
          eventId={this.state.eventId}
          portalType={this.props.portalType}
          onRetry={this.handleRetry}
          onReportBug={this.handleReportBug}
        />
      );
    }

    return this.props.children;
  }
}

interface DefaultErrorFallbackProps {
  error: Error;
  eventId: string | null;
  portalType: PortalType;
  onRetry: () => void;
  onReportBug: () => void;
}

function DefaultErrorFallback({
  error,
  eventId,
  portalType,
  onRetry,
  onReportBug,
}: DefaultErrorFallbackProps) {
  return (
    <div className='min-h-screen flex items-center justify-center bg-gray-50 px-4 py-16'>
      <div className='max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center'>
        <div className='mb-4'>
          <div className='mx-auto h-12 w-12 bg-red-100 rounded-full flex items-center justify-center'>
            <svg
              className='h-6 w-6 text-red-600'
              fill='none'
              viewBox='0 0 24 24'
              stroke='currentColor'
            >
              <path
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth={2}
                d='M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 16.5c-.77.833.192 2.5 1.732 2.5z'
              />
            </svg>
          </div>
        </div>

        <h1 className='text-lg font-semibold text-gray-900 mb-2'>Something went wrong</h1>

        <p className='text-sm text-gray-600 mb-6'>
          {process.env.NODE_ENV === 'development'
            ? error.message
            : 'An unexpected error occurred. Our team has been notified and is working to fix this issue.'}
        </p>

        {eventId && <p className='text-xs text-gray-500 mb-4 font-mono'>Error ID: {eventId}</p>}

        <div className='flex gap-3 justify-center'>
          <button
            onClick={onRetry}
            className='px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500'
          >
            Try Again
          </button>

          {eventId && (
            <button
              onClick={onReportBug}
              className='px-4 py-2 bg-gray-200 text-gray-900 text-sm font-medium rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500'
            >
              Report Issue
            </button>
          )}
        </div>

        <div className='mt-6 pt-4 border-t border-gray-200'>
          <button
            onClick={() => window.location.reload()}
            className='text-sm text-gray-500 hover:text-gray-700'
          >
            Reload Page
          </button>
        </div>
      </div>
    </div>
  );
}

// Utility function to wrap components with error boundary
export function withErrorBoundary<T extends Record<string, any>>(
  WrappedComponent: React.ComponentType<T>,
  errorBoundaryProps: Omit<ErrorBoundaryProps, 'children'>
) {
  const WithErrorBoundaryComponent = (props: T) => (
    <SentryErrorBoundary {...errorBoundaryProps}>
      <WrappedComponent {...props} />
    </SentryErrorBoundary>
  );

  WithErrorBoundaryComponent.displayName = `withErrorBoundary(${WrappedComponent.displayName || WrappedComponent.name})`;

  return WithErrorBoundaryComponent;
}
