'use client';

import { UniversalProviders } from '@dotmac/providers';
import { IntegratedAuthProvider } from '../auth/IntegratedAuthProvider';
import { queryClient } from '@/lib/query-client';
import type { ReactNode } from 'react';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <UniversalProviders
      portal='management'
      authVariant='enterprise'
      queryClient={queryClient}
      features={{
        notifications: true,
        realtime: true,
        analytics: true,
        tenantManagement: true,
        errorHandling: true,
        monitoring: true,
        security: true,
      }}
      config={{
        queryOptions: {
          staleTime: 5 * 60 * 1000, // 5 minutes
          retry: (failureCount, error: unknown) => {
            if ((error as any)?.status === 401 || (error as any)?.status === 403) {
              return false;
            }
            return failureCount < 3;
          },
        },
        notificationOptions: {
          maxNotifications: 5,
          defaultDuration: 5000,
        },
        monitoringOptions: {
          enablePerformanceTracking: true,
          enableErrorReporting: true,
          sampleRate: 0.1,
        },
      }}
    >
      <IntegratedAuthProvider>{children}</IntegratedAuthProvider>
    </UniversalProviders>
  );
}
