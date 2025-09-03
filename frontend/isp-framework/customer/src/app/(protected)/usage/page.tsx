'use client';

import { PermissionGuard } from '@dotmac/headless';

import { CustomerLayout } from '../../../components/layout/CustomerLayout';
import { UsageAnalytics } from '../../../components/usage/UsageAnalytics';

export default function UsagePage() {
  return (
    <PermissionGuard
      permissions={['usage:read']}
      fallback={
        <CustomerLayout>
          <div className='p-6 text-center'>
            <h2 className='text-lg font-medium text-gray-900 mb-2'>Access Denied</h2>
            <p className='text-gray-500'>You don't have permission to view usage analytics.</p>
          </div>
        </CustomerLayout>
      }
    >
      <CustomerLayout>
        <UsageAnalytics />
      </CustomerLayout>
    </PermissionGuard>
  );
}
