'use client';

import React, { useState, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { useSecureAuth } from '../auth/SecureAuthProvider';

interface CustomerDashboardProps {
  data?: any;
}

export function CustomerDashboard({ data: propData }: CustomerDashboardProps) {
  const { user, isAuthenticated } = useSecureAuth();
  const [error, setError] = useState<string | null>(null);

  // Use error boundary for authentication failures instead of hard redirect
  if (!isAuthenticated) {
    return (
      <div className='flex h-64 items-center justify-center'>
        <div className='text-center'>
          <AlertCircle className='mx-auto h-12 w-12 text-amber-500 mb-4' />
          <h3 className='text-lg font-semibold text-gray-900 mb-2'>Authentication Required</h3>
          <p className='text-gray-600 mb-4'>Please log in to access your customer portal.</p>
          <button 
            onClick={() => window.location.href = '/login'} 
            className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700'
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className='flex h-64 items-center justify-center'>
        <div className='text-center'>
          <AlertCircle className='mx-auto h-12 w-12 text-red-500 mb-4' />
          <h3 className='text-lg font-semibold text-gray-900 mb-2'>Something went wrong</h3>
          <p className='text-gray-600 mb-4'>{error}</p>
          <button 
            onClick={() => setError(null)} 
            className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700'
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className='rounded-lg bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 p-6 text-white shadow-lg'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold mb-2'>
              Welcome back, {user?.name || 'Customer'}! 👋
            </h1>
            <p className='text-blue-100 opacity-90'>
              Here's your service overview and account status
            </p>
          </div>
        </div>
      </div>

      {/* Service Status Overview */}
      <div className='grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4'>
        <div className='p-6 bg-white border border-gray-200 rounded-lg shadow-sm'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Connection Status</p>
              <div className='mt-2 flex items-center'>
                <span className='inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800'>
                  Active
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className='p-6 bg-white border border-gray-200 rounded-lg shadow-sm'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Monthly Usage</p>
              <div className='mt-2'>
                <p className='text-2xl font-semibold text-gray-900'>45 GB</p>
                <p className='text-sm text-gray-500'>of 100 GB</p>
              </div>
            </div>
          </div>
        </div>

        <div className='p-6 bg-white border border-gray-200 rounded-lg shadow-sm'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Current Bill</p>
              <div className='mt-2'>
                <p className='text-2xl font-semibold text-gray-900'>$89.99</p>
                <p className='text-sm text-gray-500'>Due Dec 15</p>
              </div>
            </div>
          </div>
        </div>

        <div className='p-6 bg-white border border-gray-200 rounded-lg shadow-sm'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='font-medium text-gray-600 text-sm'>Support Tickets</p>
              <div className='mt-2'>
                <p className='text-2xl font-semibold text-gray-900'>0</p>
                <p className='text-sm text-gray-500'>Open tickets</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className='bg-white border border-gray-200 rounded-lg shadow-sm p-6'>
        <h2 className='text-lg font-semibold text-gray-900 mb-4'>Quick Actions</h2>
        <div className='grid grid-cols-2 gap-3'>
          <button
            onClick={() => alert('Pay Bill clicked!')}
            className='rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-3 text-sm text-white transition-all duration-200 hover:from-blue-700 hover:to-blue-800 text-center font-medium shadow-md hover:shadow-lg'
          >
            💳 Pay Bill
          </button>
          <button
            onClick={() => alert('Get Support clicked!')}
            className='rounded-lg border-2 border-purple-300 bg-white px-4 py-3 text-purple-700 text-sm transition-all duration-200 hover:bg-purple-50 text-center font-medium'
          >
            🆘 Get Support
          </button>
          <button
            onClick={() => alert('Upgrade Service clicked!')}
            className='rounded-lg border-2 border-green-300 bg-white px-4 py-3 text-green-700 text-sm transition-all duration-200 hover:bg-green-50 text-center font-medium'
          >
            🚀 Upgrade
          </button>
          <button
            onClick={() => alert('View Bills clicked!')}
            className='rounded-lg border-2 border-gray-300 bg-white px-4 py-3 text-gray-700 text-sm transition-all duration-200 hover:bg-gray-50 text-center font-medium'
          >
            📄 View Bills
          </button>
        </div>
      </div>
    </div>
  );
}