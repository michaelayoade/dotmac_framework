'use client';

import { useTenantStore } from '@dotmac/headless';

import { AdminLayout } from '../layout/AdminLayout';
import { TenantSwitcher } from '../tenant/TenantSwitcher';

import { DashboardOverview } from './DashboardOverview';

export function AdminDashboard() {
  const { currentTenant } = useTenantStore();

  return (
    <AdminLayout>
      <div className='space-y-6'>
        {/* Header */}
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='font-bold text-2xl text-gray-900'>Dashboard</h1>
            <p className='text-gray-600'>
              Welcome to your ISP administration portal
              {currentTenant?.tenant ? ` - ${currentTenant.tenant.name}` : null}
            </p>
          </div>
          <TenantSwitcher />
        </div>

        {/* Dashboard Content */}
        <DashboardOverview />
      </div>
    </AdminLayout>
  );
}
