'use client';

import { useState, useEffect } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from '@/lib/query-client';
import { OfflineManager } from '@/lib/offline';

interface QueryProviderProps {
  children: React.ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
  // Use the singleton query client
  const [client] = useState(() => queryClient);
  const [offlineManager] = useState(() => new OfflineManager(queryClient));

  // Initialize offline manager
  useEffect(() => {
    // Offline manager is automatically initialized in constructor
    // Clean up on unmount
    return () => {
      offlineManager.destroy();
    };
  }, [offlineManager]);

  return (
    <QueryClientProvider client={client}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} position='bottom' buttonPosition='bottom-right' />
      )}
    </QueryClientProvider>
  );
}
