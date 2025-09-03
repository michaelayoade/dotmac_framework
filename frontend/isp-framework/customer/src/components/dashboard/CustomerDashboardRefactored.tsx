'use client';

import { CustomerDashboardExpanded } from '@dotmac/portal-components';

/**
 * Refactored Customer Dashboard using shared portal components
 * This replaces the complex CustomerDashboard with a unified approach
 */
export function CustomerDashboard() {
  return (
    <div className='space-y-6'>
      {/* Page Header */}
      <div>
        <h1 className='text-2xl font-bold text-gray-900'>Welcome back!</h1>
        <p className='mt-1 text-sm text-gray-600'>
          Here's an overview of your account and services
        </p>
      </div>

      {/* Dashboard Content */}
      <CustomerDashboardExpanded />
    </div>
  );
}
