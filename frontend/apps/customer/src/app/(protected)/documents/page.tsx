'use client';

import { PermissionGuard } from '@dotmac/headless';

import { DocumentManager } from '../../../components/documents/DocumentManager';
import { CustomerLayout } from '../../../components/layout/CustomerLayout';

export default function DocumentsPage() {
  return (
    <PermissionGuard 
      permissions={['documents:read']}
      fallback={
        <CustomerLayout>
          <div className="p-6 text-center">
            <h2 className="text-lg font-medium text-gray-900 mb-2">Access Denied</h2>
            <p className="text-gray-500">You don't have permission to view documents.</p>
          </div>
        </CustomerLayout>
      }
    >
      <CustomerLayout>
        <DocumentManager />
      </CustomerLayout>
    </PermissionGuard>
  );
}
