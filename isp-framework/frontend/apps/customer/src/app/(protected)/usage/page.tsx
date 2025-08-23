'use client';

import { PermissionGuard } from '@dotmac/headless';

import { CustomerLayout } from '../../../components/layout/CustomerLayout';
import { UsageAnalytics } from '../../../components/usage/UsageAnalytics';

export default function UsagePage() {
  return (
    <PermissionGuard permissions={['usage:read']}>
      <CustomerLayout>
        <UsageAnalytics />
      </CustomerLayout>
    </PermissionGuard>
  );
}
