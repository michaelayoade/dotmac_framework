'use client';

import { RouteGuard } from '@dotmac/headless';

import { RouteProtectionDemo } from '../../../components/demo/RouteProtectionDemo';
import { AdminLayout } from '../../../components/layout/AdminLayout';

export default function SecurityPage() {
  return (
    <RouteGuard
      requiredPermissions={['security:read']}
      requiredRoles={['tenant-admin', 'super-admin']}
    >
      <AdminLayout>
        <div className='space-y-6'>
          <div className='flex items-center justify-between'>
            <h1 className='font-bold text-2xl text-gray-900'>Security & Access Control</h1>
            <RouteGuard
              requiredPermissions={['security:write']}
              requiredRoles={['super-admin']}
              fallback={null}
            >
              <button
                type='button'
                className='rounded-lg bg-red-600 px-4 py-2 text-white transition-colors hover:bg-red-700'
              >
                Security Settings
              </button>
            </RouteGuard>
          </div>

          <RouteProtectionDemo />
        </div>
      </AdminLayout>
    </RouteGuard>
  );
}
