'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState, useEffect } from 'react';
import { AuthProvider } from '@/components/auth/AuthProvider';
import { TenantProvider } from '@/lib/tenant-context';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ToastProvider } from '@/components/ui/Toast';
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

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <TenantProvider>
            <ToastProvider>
              {children}
            </ToastProvider>
          </TenantProvider>
        </AuthProvider>
        {process.env.NODE_ENV === 'development' && (
          <ReactQueryDevtools initialIsOpen={false} />
        )}
      </QueryClientProvider>
    </ErrorBoundary>
  );
}