'use client';

import { useAuth, useTenantStore } from '@dotmac/headless';
import { type ReactNode, useEffect } from 'react';

interface TenantProviderProps {
  children: ReactNode;
}

export function TenantProvider({ children }: TenantProviderProps) {
  const { user } = useAuth();
  const { currentTenant, loadTenantPermissions } = useTenantStore();

  useEffect(() => {
    // Load tenant permissions when user or tenant changes
    if (user && currentTenant?.tenant?.id) {
      loadTenantPermissions(currentTenant.tenant.id);
    }
  }, [user, currentTenant?.tenant?.id, loadTenantPermissions]);

  return <>{children}</>;
}
