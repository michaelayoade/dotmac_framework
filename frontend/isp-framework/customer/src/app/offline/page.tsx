/**
 * Offline Page
 * Shown when user is offline and content is not cached
 */

'use client';

import { useEffect, useState } from 'react';
import { networkMonitor } from '../../lib/utils/serviceWorker';

export default function OfflinePage() {
  const [isOnline, setIsOnline] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    setIsOnline(networkMonitor.isOnline());

    const cleanup = networkMonitor.onStatusChange((online) => {
      setIsOnline(online);
      if (online) {
        // Redirect back to dashboard when online
        setTimeout(() => {
          window.location.href = '/dashboard';
        }, 2000);
      }
    });

    return cleanup;
  }, []);

  const handleRetry = () => {
    setRetryCount((prev) => prev + 1);

    if (networkMonitor.isOnline()) {
      window.location.href = '/dashboard';
    } else {
      // Attempt to refresh the page
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    }
  };

  return (
    <div className='min-h-screen bg-gray-50 flex items-center justify-center px-4'>
      <div className='max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center'>
        {/* Offline Icon */}
        <div className='mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-6'>
          {isOnline ? (
            <svg
              className='w-12 h-12 text-green-500'
              fill='none'
              stroke='currentColor'
              viewBox='0 0 24 24'
            >
              <path
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth={2}
                d='M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0'
              />
            </svg>
          ) : (
            <svg
              className='w-12 h-12 text-red-500'
              fill='none'
              stroke='currentColor'
              viewBox='0 0 24 24'
            >
              <path
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth={2}
                d='M18.364 5.636l-12.728 12.728m0-12.728l12.728 12.728'
              />
            </svg>
          )}
        </div>

        {/* Status Message */}
        <h1 className='text-2xl font-bold text-gray-900 mb-4'>
          {isOnline ? 'Back Online!' : "You're Offline"}
        </h1>

        <p className='text-gray-600 mb-8'>
          {isOnline
            ? 'Great! Your internet connection has been restored. Redirecting you back...'
            : "It looks like you've lost your internet connection. Some features may not be available until you're back online."}
        </p>

        {/* Connection Status */}
        <div className='mb-8'>
          <div
            className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-medium ${
              isOnline ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}
          >
            <div
              className={`w-2 h-2 rounded-full mr-2 ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}
            ></div>
            {isOnline ? 'Connected' : 'Disconnected'}
          </div>
        </div>

        {/* Cached Content Notice */}
        {!isOnline && (
          <div className='bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6'>
            <div className='flex items-start'>
              <svg
                className='w-5 h-5 text-blue-500 mr-3 mt-0.5'
                fill='currentColor'
                viewBox='0 0 20 20'
              >
                <path
                  fillRule='evenodd'
                  d='M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z'
                  clipRule='evenodd'
                />
              </svg>
              <div>
                <h3 className='text-sm font-medium text-blue-800 mb-1'>Limited Functionality</h3>
                <p className='text-sm text-blue-700'>
                  You can still view some previously cached content, but real-time data and actions
                  won't be available.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className='space-y-4'>
          <button
            onClick={handleRetry}
            disabled={isOnline}
            className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
              isOnline
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {retryCount > 0 ? `Retry (${retryCount})` : 'Try Again'}
          </button>

          <button
            onClick={() => window.history.back()}
            className='w-full py-3 px-4 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition-colors'
          >
            Go Back
          </button>
        </div>

        {/* Troubleshooting Tips */}
        {!isOnline && (
          <div className='mt-8 pt-6 border-t border-gray-200'>
            <h3 className='text-sm font-medium text-gray-900 mb-3'>Troubleshooting Tips:</h3>
            <ul className='text-sm text-gray-600 space-y-1 text-left'>
              <li>• Check your internet connection</li>
              <li>• Make sure airplane mode is off</li>
              <li>• Try switching between WiFi and mobile data</li>
              <li>• Contact your internet service provider if the problem persists</li>
            </ul>
          </div>
        )}

        {/* Network Info */}
        {networkMonitor.getConnection() && (
          <div className='mt-4 text-xs text-gray-500'>
            Connection type: {networkMonitor.getConnectionType().toUpperCase()}
          </div>
        )}
      </div>
    </div>
  );
}
