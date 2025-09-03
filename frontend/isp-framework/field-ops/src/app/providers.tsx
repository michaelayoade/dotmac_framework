'use client';

import { PortalProviderFactory, PackageIntegrations } from '@dotmac/portal-components';
import { MobileProvider } from '@dotmac/mobile';
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
            staleTime: 10 * 60 * 1000, // 10 minutes for offline-first
            retry: (failureCount, error: unknown) => {
              if ((error as any)?.status === 401 || (error as any)?.status === 403) {
                return false;
              }
              return failureCount < 2; // Less retries for mobile
            },
          },
        },
      })
  );

  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || 'technician';
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  return (
    <PortalProviderFactory
      config={{
        portal: 'technician',
        authVariant: 'enterprise',
        apiBaseUrl,
        queryClient,
        features: {
          notifications: true,
          realtime: true,
          analytics: false,
          tenantManagement: false,
          errorHandling: true,
          toasts: true,
          devtools: process.env.NODE_ENV === 'development',
        },
      }}
      customProviders={
        <MobileProvider
          config={{
            enableOptimizations: true,
            offline: {
              backgroundSync: true,
              notifications: true,
              storageQuota: 100, // 100MB for field operations
              autoCleanup: true,
              cacheDays: 30,
              compression: true,
            },
            cache: {
              useIndexedDB: true,
              cacheAssets: true,
              maxCacheSize: 200, // 200MB
              prefetchStrategy: 'conservative',
            },
            pwa: {
              swPath: '/sw.js',
              autoUpdate: true,
              updateInterval: 300000, // 5 minutes
              showInstallPrompt: true,
              installPromptDelay: 30000, // 30 seconds
              offlineIndicator: true,
              pushNotifications: true,
              appName: 'DotMac Technician',
            },
            debug: process.env.NODE_ENV === 'development',
          }}
        >
          <PackageIntegrations
            tenantId={tenantId}
            enableNetwork={true} // Technicians need network diagnostics
            enableAssets={true} // Technicians manage field equipment
            enableJourneys={false} // Not needed for technician workflow
          >
            {children}
          </PackageIntegrations>
        </MobileProvider>
      }
    >
      {children}
    </PortalProviderFactory>
  );
}
