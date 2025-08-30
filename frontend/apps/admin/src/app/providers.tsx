'use client';

import { PortalProviderFactory, PackageIntegrations } from '@dotmac/portal-components';
import { createApiClient } from '@dotmac/headless';
import { QueryClient } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import type { ReactNode } from 'react';

import { setupGlobalErrorHandling } from '../lib/errorBoundary';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(() => {
    const client = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 5 * 60 * 1000, // 5 minutes
          retry: (failureCount, error: any) => {
            // Don't retry on auth errors
            if (error?.status === 401 || error?.status === 403) {
              return false;
            }
            return failureCount < 3;
          },
        },
      },
    });

    // Initialize API client synchronously
    createApiClient({
      baseUrl: process.env.NEXT_PUBLIC_API_URL || '/api',
      timeout: 10000,
    });

    return client;
  });

  // Setup global error handling on client-side
  useEffect(() => {
    setupGlobalErrorHandling();
  }, []);

  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || 'admin';
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || '/api';

  return (
    <PortalProviderFactory
      config={{
        portal: 'management',
        authVariant: 'enterprise',
        apiBaseUrl,
        queryClient,
        features: {
          notifications: true,
          realtime: false,
          analytics: true,
          tenantManagement: true,
          errorHandling: true,
          toasts: true,
          devtools: process.env.NODE_ENV === 'development',
          enableBatchOperations: true,
          enableRealTimeSync: true,
          enableAdvancedAnalytics: true,
          enableAuditLogging: true
        }
      }}
      customProviders={
        <PackageIntegrations
          tenantId={tenantId}
          enableNetwork={true}
          enableAssets={true}
          enableJourneys={true}
        >
          {children}
        </PackageIntegrations>
      }
    >
      {children}
    </PortalProviderFactory>
  );
}
