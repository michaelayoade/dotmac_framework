'use client';

import { NotificationProvider } from '@dotmac/primitives';
import { ThemeProvider } from '@dotmac/styled-components';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createApiClient } from '@dotmac/headless';
import type { ReactNode } from 'react';
import { useEffect } from 'react';

import { AuthProvider } from '../components/auth/AuthProvider';
import { TenantProvider } from '../components/tenant/TenantProvider';
import { setupGlobalErrorHandling } from '../lib/errorBoundary';

// Initialize API client synchronously before any components render
createApiClient({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || '/api',
  timeout: 10000,
});

const queryClient = new QueryClient({
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

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  // Setup global error handling on client-side
  useEffect(() => {
    setupGlobalErrorHandling();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider portal='admin'>
        <AuthProvider>
          <TenantProvider>
            <NotificationProvider maxNotifications={5} defaultDuration={5000}>
              {children}
            </NotificationProvider>
          </TenantProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
