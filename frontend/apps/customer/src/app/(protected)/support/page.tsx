'use client';

import { PermissionGuard } from '@dotmac/headless';

import { CustomerLayout } from '../../../components/layout/CustomerLayout';
import { SupportTickets } from '../../../components/support/SupportTickets';

export default function SupportPage() {
  return (
    <PermissionGuard permissions={['support:read']}>
      <CustomerLayout>
        <SupportTickets />
      </CustomerLayout>
    </PermissionGuard>
  );
}
