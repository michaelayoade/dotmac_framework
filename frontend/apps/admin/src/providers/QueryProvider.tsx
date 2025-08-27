/**
 * React Query Provider
 * Configures React Query for the entire application with optimized defaults
 */

'use client';

import { useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { showErrorNotification } from '../stores/appStore';

interface QueryProviderProps {
  children: ReactNode;
}

// Create Query Client with optimized configuration
function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Stale time - data is considered fresh for this duration
        staleTime: 5 * 60 * 1000, // 5 minutes
        
        // Garbage collection time - how long to keep unused data
        gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
        
        // Retry configuration
        retry: (failureCount, error: any) => {
          // Don't retry for authentication errors
          if (error?.status === 401 || error?.status === 403) {
            return false;
          }
          // Retry up to 3 times for other errors
          return failureCount < 3;
        },
        
        // Retry delay with exponential backoff
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        
        // Background refetch settings
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        refetchOnMount: true,
        
        // Network mode - fail when offline
        networkMode: 'online',
      },
      mutations: {
        // Retry mutations only once
        retry: 1,
        
        // Global error handler for mutations
        onError: (error: any, variables, context) => {
          console.error('Mutation error:', error);
          
          // Don't show notification for specific error types
          if (error?.status === 401 || error?.status === 403) {
            // Authentication errors are handled by auth store
            return;
          }
          
          // Show user-friendly error notification
          const message = error?.message || 'An unexpected error occurred';
          showErrorNotification('Operation Failed', message);
        },
      },
    },
  });
}

export function QueryProvider({ children }: QueryProviderProps) {
  // Create query client in state to avoid creating new instance on re-renders
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools
          initialIsOpen={false}
          position="bottom-right"
          buttonPosition="bottom-right"
        />
      )}
    </QueryClientProvider>
  );
}