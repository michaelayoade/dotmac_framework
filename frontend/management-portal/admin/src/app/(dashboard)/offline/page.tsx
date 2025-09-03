'use client';

import React from 'react';
import {
  WifiIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { usePWA } from '@/lib/pwa-manager';

export default function OfflinePage() {
  const { isOnline } = usePWA();

  const handleRetry = () => {
    window.location.reload();
  };

  if (isOnline) {
    // If we're online but still on this page, redirect to dashboard
    window.location.href = '/dashboard';
    return null;
  }

  return (
    <div className='min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4'>
      <div className='max-w-lg w-full'>
        <div className='bg-white rounded-lg shadow-xl p-8 text-center'>
          {/* Icon */}
          <div className='mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-6'>
            <WifiIcon className='w-8 h-8 text-blue-600' />
          </div>

          {/* Title */}
          <h1 className='text-2xl font-bold text-gray-900 mb-4'>You're Currently Offline</h1>

          {/* Description */}
          <p className='text-gray-600 mb-6 leading-relaxed'>
            No internet connection detected. Don't worry - you can still access some features of the
            Management Admin Portal. Your changes will be synced when you reconnect.
          </p>

          {/* Offline Features */}
          <div className='bg-gray-50 rounded-lg p-4 mb-6'>
            <h3 className='text-sm font-semibold text-gray-900 mb-3'>
              Available Offline Features:
            </h3>
            <ul className='space-y-2 text-sm text-gray-600'>
              <li className='flex items-center'>
                <CheckCircleIcon className='w-4 h-4 text-green-500 mr-2 flex-shrink-0' />
                View cached tenant information
              </li>
              <li className='flex items-center'>
                <CheckCircleIcon className='w-4 h-4 text-green-500 mr-2 flex-shrink-0' />
                Access recently viewed dashboard data
              </li>
              <li className='flex items-center'>
                <CheckCircleIcon className='w-4 h-4 text-green-500 mr-2 flex-shrink-0' />
                Review cached user profiles
              </li>
              <li className='flex items-center'>
                <ExclamationTriangleIcon className='w-4 h-4 text-amber-500 mr-2 flex-shrink-0' />
                Limited functionality for new operations
              </li>
            </ul>
          </div>

          {/* Actions */}
          <div className='space-y-4'>
            <button
              onClick={handleRetry}
              className='w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center'
            >
              <ArrowPathIcon className='w-4 h-4 mr-2' />
              Try Again
            </button>

            <button
              onClick={() => window.history.back()}
              className='w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 px-4 rounded-lg transition-colors duration-200'
            >
              Go Back
            </button>
          </div>

          {/* Connection Status */}
          <div className='mt-6 pt-6 border-t border-gray-200'>
            <div className='flex items-center justify-center text-sm text-gray-500'>
              <div className='w-2 h-2 bg-red-400 rounded-full mr-2'></div>
              Offline Mode Active
            </div>
          </div>
        </div>

        {/* PWA Info */}
        <div className='mt-6 text-center'>
          <p className='text-sm text-gray-500'>
            This app works offline thanks to Progressive Web App technology.
          </p>
        </div>
      </div>
    </div>
  );
}
