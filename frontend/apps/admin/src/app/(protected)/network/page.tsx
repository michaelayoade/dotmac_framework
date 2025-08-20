'use client';

import { NetworkEngineerGuard } from '@dotmac/headless';

import { AdminLayout } from '../../../components/layout/AdminLayout';

export default function NetworkPage() {
  return (
    <NetworkEngineerGuard>
      <AdminLayout>
        <div className='space-y-6'>
          <div className='flex items-center justify-between'>
            <h1 className='font-bold text-2xl text-gray-900'>Network Management</h1>
            <div className='flex space-x-2'>
              <button
                type='button'
                className='rounded-lg bg-primary px-4 py-2 text-white transition-colors hover:bg-primary/90'
              >
                Add Device
              </button>
              <button
                type='button'
                className='rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50'
              >
                Network Scan
              </button>
            </div>
          </div>

          <div className='rounded-lg bg-white p-6 shadow'>
            <h2 className='mb-4 font-semibold text-gray-900 text-lg'>Network Infrastructure</h2>
            <p className='text-gray-600'>
              Network device management, topology visualization, and monitoring tools would be
              implemented here.
            </p>
            <p className='mt-2 text-green-600 text-sm'>
              ✓ Access granted: Network Engineer permissions verified
            </p>
          </div>
        </div>
      </AdminLayout>
    </NetworkEngineerGuard>
  );
}
