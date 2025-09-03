'use client';

import { Suspense } from 'react';
import { CustomerDashboardRefactored } from '../components/dashboard/CustomerDashboardRefactored';
import { useCustomerDashboardData } from '../lib/api/customerApi';

function CustomerDashboardContainer() {
  const { data, isLoading, error, refetch } = useCustomerDashboardData();

  if (isLoading) {
    return (
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6'>
        {[...Array(6)].map((_, i) => (
          <div key={i} className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
            <div className='animate-pulse'>
              <div className='h-4 bg-gray-200 rounded w-3/4 mb-2'></div>
              <div className='h-8 bg-gray-200 rounded w-1/2'></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className='flex flex-col items-center justify-center p-8'>
        <div className='bg-red-50 border border-red-200 rounded-lg p-6 max-w-md'>
          <h3 className='text-lg font-semibold text-red-800 mb-2'>Unable to Load Dashboard</h3>
          <p className='text-red-600 mb-4'>{error}</p>
          <button
            onClick={refetch}
            className='bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md transition-colors'
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className='flex items-center justify-center p-8'>
        <p className='text-gray-600'>No dashboard data available</p>
      </div>
    );
  }

  return <CustomerDashboardRefactored data={data} />;
}

export default function CustomerHomePage() {
  return (
    <Suspense
      fallback={
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6'>
          {[...Array(6)].map((_, i) => (
            <div key={i} className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
              <div className='animate-pulse'>
                <div className='h-4 bg-gray-200 rounded w-3/4 mb-2'></div>
                <div className='h-8 bg-gray-200 rounded w-1/2'></div>
              </div>
            </div>
          ))}
        </div>
      }
    >
      <CustomerDashboardContainer />
    </Suspense>
  );
}
