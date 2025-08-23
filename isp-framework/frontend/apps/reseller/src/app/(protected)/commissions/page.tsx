'use client';

import { PermissionGuard } from '@dotmac/headless';

import { ResellerLayout } from '../../../components/layout/ResellerLayout';

export default function CommissionsPage() {
  return (
    <PermissionGuard permissions={['commissions:read']}>
      <ResellerLayout>
        <div className='space-y-6'>
          <div className='flex items-center justify-between'>
            <h1 className='font-bold text-2xl text-gray-900'>Commission Tracking</h1>
            <button
              type='button'
              className='rounded-lg bg-green-600 px-4 py-2 text-white transition-colors hover:bg-green-700'
            >
              Generate Report
            </button>
          </div>

          <div className='grid grid-cols-1 gap-6 lg:grid-cols-3'>
            <div className='rounded-lg bg-white p-6 shadow'>
              <h2 className='mb-4 font-semibold text-gray-900 text-lg'>This Month</h2>
              <p className='font-bold text-3xl text-green-600'>$2,289.00</p>
              <p className='text-gray-500 text-sm'>Pending commission</p>
            </div>

            <div className='rounded-lg bg-white p-6 shadow'>
              <h2 className='mb-4 font-semibold text-gray-900 text-lg'>Total Earned</h2>
              <p className='font-bold text-3xl text-gray-900'>$24,382.50</p>
              <p className='text-gray-500 text-sm'>All-time earnings</p>
            </div>

            <div className='rounded-lg bg-white p-6 shadow'>
              <h2 className='mb-4 font-semibold text-gray-900 text-lg'>Next Payout</h2>
              <p className='font-semibold text-gray-900 text-lg'>February 15, 2024</p>
              <p className='text-green-600 text-sm'>$2,289.00 pending</p>
            </div>
          </div>

          <div className='rounded-lg bg-white p-6 shadow'>
            <h2 className='mb-4 font-semibold text-gray-900 text-lg'>Commission History</h2>
            <p className='text-gray-600'>
              Detailed commission tracking, payout history, and performance metrics would be
              displayed here.
            </p>
            <p className='mt-2 text-green-600 text-sm'>
              ✓ Commission access verified for reseller account
            </p>
          </div>
        </div>
      </ResellerLayout>
    </PermissionGuard>
  );
}
