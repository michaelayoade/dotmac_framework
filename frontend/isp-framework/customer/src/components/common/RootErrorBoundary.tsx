'use client';

import { AlertTriangle } from 'lucide-react';
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class RootErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ error, errorInfo });

    // Log to monitoring service
    console.error('RootErrorBoundary caught an error:', error);
    console.error('Component stack:', errorInfo.componentStack);

    // Send to error tracking
    if (typeof window !== 'undefined') {
      // Send to Sentry or other error tracking
      window.gtag?.('event', 'exception', {
        description: error.message,
        fatal: false,
      });
    }
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleRetry = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      // Render custom fallback UI or use provided fallback
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className='min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8'>
          <div className='max-w-md w-full space-y-8'>
            <div className='text-center'>
              <AlertTriangle className='mx-auto h-24 w-24 text-red-500' />
              <h1 className='mt-6 text-3xl font-extrabold text-gray-900'>Something went wrong</h1>
              <p className='mt-2 text-sm text-gray-600'>
                We apologize for the inconvenience. An unexpected error has occurred.
              </p>

              {process.env.NODE_ENV === 'development' && this.state.error && (
                <details className='mt-4 text-left'>
                  <summary className='cursor-pointer text-sm text-gray-500 hover:text-gray-700'>
                    Error Details (Development Only)
                  </summary>
                  <pre className='mt-2 text-xs bg-gray-100 p-4 rounded-md overflow-auto max-h-60'>
                    <strong>Error:</strong> {this.state.error.message}
                    {'\n\n'}
                    <strong>Stack:</strong> {this.state.error.stack}
                    {'\n\n'}
                    <strong>Component Stack:</strong> {this.state.errorInfo?.componentStack}
                  </pre>
                </details>
              )}
            </div>

            <div className='flex flex-col sm:flex-row gap-3 justify-center'>
              <button
                onClick={this.handleRetry}
                type='button'
                className='w-full sm:w-auto inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
              >
                Try Again
              </button>

              <button
                onClick={this.handleReload}
                type='button'
                className='w-full sm:w-auto inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
              >
                Reload Page
              </button>

              <a
                href='/'
                className='w-full sm:w-auto inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
              >
                Go Home
              </a>
            </div>

            <div className='text-center'>
              <p className='text-xs text-gray-500'>
                If this problem persists, please contact{' '}
                <a href='mailto:support@dotmac.com' className='text-blue-600 hover:text-blue-500'>
                  support@dotmac.com
                </a>
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
