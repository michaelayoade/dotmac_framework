'use client';

import { PortalProviderFactory, PackageIntegrations } from '@dotmac/portal-components';
import { QueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { ReactNode } from 'react';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
            retry: (failureCount, error: unknown) => {
              if ((error as any)?.status === 401 || (error as any)?.status === 403) {
                return false;
              }
              return failureCount < 3;
            },
          },
        },
      })
  );

  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || 'customer';
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  return (
    <PortalProviderFactory
      config={{
        portal: 'customer',
        authVariant: 'customer',
        apiBaseUrl,
        queryClient,
        features: {
          notifications: true,
          realtime: false,
          analytics: false,
          tenantManagement: true,
          errorHandling: true,
          toasts: true,
          devtools: process.env.NODE_ENV === 'development',
        },
      }}
      customProviders={
        <PackageIntegrations
          tenantId={tenantId}
          enableNetwork={false} // Customers don't need network management
          enableAssets={false} // Customers don't need asset management
          enableJourneys={true} // Enable journey tracking for customer experience
        >
          {children}
        </PackageIntegrations>
      }
    >
      {children}
    </PortalProviderFactory>
  );
}
