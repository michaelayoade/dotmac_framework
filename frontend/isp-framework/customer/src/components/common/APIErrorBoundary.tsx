'use client';

import { AlertCircle, RefreshCw, Wifi } from 'lucide-react';
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onRetry?: () => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorType: 'network' | 'api' | 'unknown';
  retryCount: number;
}

export class APIErrorBoundary extends Component<Props, State> {
  private maxRetries = 3;
  private retryTimeouts: NodeJS.Timeout[] = [];

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      errorType: 'unknown',
      retryCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Analyze error type
    let errorType: 'network' | 'api' | 'unknown' = 'unknown';

    if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
      errorType = 'network';
    } else if (
      error.message.includes('API') ||
      error.message.includes('401') ||
      error.message.includes('403')
    ) {
      errorType = 'api';
    }

    return {
      hasError: true,
      error,
      errorType,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ error, errorInfo });

    // Log API errors with more context
    console.error('APIErrorBoundary caught an error:', error);
    console.error('Error type:', this.state.errorType);

    // Send to monitoring with API error context
    if (typeof window !== 'undefined') {
      window.gtag?.('event', 'api_error', {
        error_type: this.state.errorType,
        error_message: error.message,
        fatal: false,
      });
    }
  }

  componentWillUnmount() {
    // Clear any pending retry timeouts
    this.retryTimeouts.forEach((timeout) => clearTimeout(timeout));
  }

  private handleRetry = () => {
    if (this.state.retryCount >= this.maxRetries) {
      return;
    }

    this.setState((prevState) => ({
      retryCount: prevState.retryCount + 1,
    }));

    // Progressive backoff: 1s, 3s, 5s
    const delay = (this.state.retryCount + 1) * 1000 + this.state.retryCount * 2000;

    const timeout = setTimeout(() => {
      this.setState({
        hasError: false,
        error: undefined,
        retryCount: 0,
      });

      // Call custom retry handler if provided
      this.props.onRetry?.();
    }, delay);

    this.retryTimeouts.push(timeout);
  };

  private handleRefresh = () => {
    window.location.reload();
  };

  private getErrorIcon() {
    switch (this.state.errorType) {
      case 'network':
        return <Wifi className='h-16 w-16 text-orange-500' />;
      case 'api':
        return <AlertCircle className='h-16 w-16 text-red-500' />;
      default:
        return <AlertCircle className='h-16 w-16 text-gray-500' />;
    }
  }

  private getErrorMessage() {
    switch (this.state.errorType) {
      case 'network':
        return {
          title: 'Connection Problem',
          message: 'Unable to connect to our servers. Please check your internet connection.',
        };
      case 'api':
        return {
          title: 'Service Unavailable',
          message: "Our service is temporarily unavailable. We're working to fix this.",
        };
      default:
        return {
          title: 'Something Went Wrong',
          message: 'An unexpected error occurred while loading your data.',
        };
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { title, message } = this.getErrorMessage();
      const canRetry = this.state.retryCount < this.maxRetries;

      return (
        <div className='flex flex-col items-center justify-center p-8 text-center min-h-64'>
          {this.getErrorIcon()}

          <h3 className='mt-4 text-lg font-semibold text-gray-900'>{title}</h3>

          <p className='mt-2 text-sm text-gray-600 max-w-sm'>{message}</p>

          {this.state.retryCount > 0 && (
            <p className='mt-2 text-xs text-gray-500'>
              Retry attempt {this.state.retryCount} of {this.maxRetries}
            </p>
          )}

          <div className='mt-6 flex flex-col sm:flex-row gap-3'>
            {canRetry && (
              <button
                onClick={this.handleRetry}
                type='button'
                className='inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50'
              >
                <RefreshCw className='h-4 w-4 mr-2' />
                Try Again
              </button>
            )}

            <button
              onClick={this.handleRefresh}
              type='button'
              className='inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
            >
              Refresh Page
            </button>
          </div>

          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className='mt-6 text-left max-w-md'>
              <summary className='cursor-pointer text-xs text-gray-500 hover:text-gray-700'>
                Error Details (Development)
              </summary>
              <pre className='mt-2 text-xs bg-gray-100 p-3 rounded text-left overflow-auto max-h-32'>
                {this.state.error.message}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
