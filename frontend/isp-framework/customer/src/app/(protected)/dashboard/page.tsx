/**
 * Dashboard Page with Lazy Loading
 * Optimized for performance with code splitting
 */

'use client';

import { Suspense } from 'react';
import { ErrorBoundary as ComponentErrorBoundary } from '@dotmac/providers';
import { LazyCustomerDashboard } from '../../../components/lazy/LazyComponents';

export default function DashboardPage() {
  return (
    <div className='min-h-screen bg-gray-50'>
      <ComponentErrorBoundary portal='customer'>
        <Suspense
          fallback={
            <div className='animate-pulse p-6'>
              <div className='h-8 bg-gray-200 rounded w-48 mb-6'></div>
              <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8'>
                {[...Array(4)].map((_, i) => (
                  <div key={i} className='h-32 bg-gray-200 rounded-lg'></div>
                ))}
              </div>
              <div className='h-64 bg-gray-200 rounded-lg mb-6'></div>
              <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
                <div className='h-48 bg-gray-200 rounded-lg'></div>
                <div className='h-48 bg-gray-200 rounded-lg'></div>
              </div>
            </div>
          }
        >
          <LazyCustomerDashboard />
        </Suspense>
      </ComponentErrorBoundary>
    </div>
  );
}
