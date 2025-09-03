/**
 * Minimal Providers - Production-ready providers with unified management operations
 * Leverages existing systems architecture
 */

import React, { ReactNode } from 'react';
import { ManagementProvider } from '@dotmac/headless/management';

interface MinimalProvidersProps {
  children: ReactNode;
}

export function MinimalProviders({ children }: MinimalProvidersProps) {
  const apiBaseUrl = process.env.NEXT_PUBLIC_ISP_API_URL || 'http://localhost:8000/api/v1';

  return (
    <div className='min-h-screen'>
      <ManagementProvider
        portalType='admin'
        apiBaseUrl={apiBaseUrl}
        enablePerformanceMonitoring={true}
        enableErrorBoundary={true}
        initialConfig={{
          enableOptimisticUpdates: true,
          enableRealTimeSync: true,
          autoRefreshInterval: 60000,
        }}
        features={{
          enableBatchOperations: false,
          enableRealTimeSync: true,
          enableAdvancedAnalytics: true,
          enableAuditLogging: true,
        }}
      >
        {children}
      </ManagementProvider>
    </div>
  );
}
