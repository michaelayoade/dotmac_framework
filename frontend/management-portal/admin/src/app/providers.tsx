'use client';

// Smart component loading with graceful fallbacks
import { createAdaptiveComponent } from '@/components/adapters/ComponentLoader';
import { PortalProviderFactory as FallbackPortalProviderFactory } from '@/components/temp/PortalProviderFactory';
import { PackageIntegrations as FallbackPackageIntegrations } from '@/components/temp/PackageIntegrations';
import { ManagementProvider as FallbackManagementProvider } from '@/components/temp/ManagementProvider';

// Create adaptive components that try real packages first, fallback to stubs
const PortalProviderFactory = createAdaptiveComponent(
  '@dotmac/portal-components',
  'PortalProviderFactory',
  FallbackPortalProviderFactory
);

const PackageIntegrations = createAdaptiveComponent(
  '@dotmac/portal-components',
  'PackageIntegrations',
  FallbackPackageIntegrations
);

const ManagementProvider = createAdaptiveComponent(
  '@dotmac/headless',
  'ManagementProvider',
  FallbackManagementProvider
);
import { useState, useEffect } from 'react';
import { createProductionQueryClient } from '@/lib/production-init';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => createProductionQueryClient());

  // Initialize production systems (client-side only)
  useEffect(() => {
    // Ensure this only runs on the client
    if (typeof window === 'undefined') return;

    const initProduction = async () => {
      try {
        // Dynamic import to avoid server-side bundling
        const { createProductionInitializer } = await import('@/lib/production-init');
        const initializer = createProductionInitializer();
        await initializer.initialize(queryClient);
      } catch (error) {
        console.error('Failed to initialize production systems:', error);
      }
    };

    // Delay initialization to ensure DOM is ready
    const timer = setTimeout(initProduction, 100);
    return () => clearTimeout(timer);
  }, [queryClient]);

  const managementApiUrl =
    process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'http://localhost:8001/api/v1';
  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || 'management';

  return (
    <PortalProviderFactory
      config={{
        portal: 'management-admin',
        authVariant: 'enterprise',
        apiBaseUrl: managementApiUrl,
        queryClient,
        productionInit: true,
        features: {
          notifications: true,
          realtime: true,
          analytics: true,
          tenantManagement: true,
          errorHandling: true,
          toasts: true,
          devtools: process.env.NODE_ENV === 'development',
          enableBatchOperations: true,
          enableRealTimeSync: true,
          enableAdvancedAnalytics: true,
          enableAuditLogging: true,
        },
      }}
      customProviders={
        <PackageIntegrations
          tenantId={tenantId}
          enableNetwork={true}
          enableAssets={true}
          enableJourneys={true}
        >
          <ManagementProvider
            portalType='management-admin'
            apiBaseUrl={managementApiUrl}
            enablePerformanceMonitoring={true}
            enableErrorBoundary={true}
            initialConfig={{
              enableOptimisticUpdates: false, // More conservative for management
              enableRealTimeSync: true,
              autoRefreshInterval: 30000, // More frequent updates
              retryFailedOperations: true,
            }}
            features={{
              enableBatchOperations: true, // Enable for management admin
              enableRealTimeSync: true,
              enableAdvancedAnalytics: true,
              enableAuditLogging: true,
            }}
          >
            {children}
          </ManagementProvider>
        </PackageIntegrations>
      }
    >
      {children}
    </PortalProviderFactory>
  );
}
