'use client';

import { PermissionGuard } from '@dotmac/headless';

import { DocumentManager } from '../../../components/documents/DocumentManager';
import { CustomerLayout } from '../../../components/layout/CustomerLayout';

export default function DocumentsPage() {
  return (
    <PermissionGuard permissions={['documents:read']}>
      <CustomerLayout>
        <DocumentManager />
      </CustomerLayout>
    </PermissionGuard>
  );
}
