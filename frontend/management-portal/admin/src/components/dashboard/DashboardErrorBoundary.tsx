'use client';

import { Component, ReactNode } from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class DashboardErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Dashboard Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className='min-h-screen flex items-center justify-center bg-gray-50'>
          <div className='max-w-md w-full bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
            <div className='flex items-center mb-4'>
              <ExclamationTriangleIcon className='h-8 w-8 text-red-500 mr-3' />
              <h2 className='text-lg font-semibold text-gray-900'>Dashboard Error</h2>
            </div>
            <p className='text-gray-600 mb-4'>
              We encountered an error loading the dashboard. This might be due to:
            </p>
            <ul className='list-disc list-inside text-sm text-gray-500 mb-6 space-y-1'>
              <li>Backend API connection issues</li>
              <li>Authentication problems</li>
              <li>Temporary server issues</li>
            </ul>
            <div className='flex space-x-3'>
              <button
                onClick={() => window.location.reload()}
                className='flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors'
              >
                Reload Page
              </button>
              <button
                onClick={() => (window.location.href = '/login')}
                className='flex-1 bg-gray-100 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-200 transition-colors'
              >
                Re-login
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className='mt-4 text-xs'>
                <summary className='cursor-pointer text-gray-500'>
                  Error Details (Development)
                </summary>
                <pre className='mt-2 p-2 bg-gray-100 rounded text-red-600 overflow-auto'>
                  {this.state.error.message}
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
