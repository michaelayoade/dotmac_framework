'use client';

import { ManagementAuthProvider } from '@/components/auth/ManagementAuthProvider';
import { QueryProvider } from './QueryProvider';
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import { NotificationProvider } from '@/components/ui/NotificationProvider';
import { LoadingOverlay } from '@/components/ui/LoadingOverlay';

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <ErrorBoundary>
      <QueryProvider>
        <ManagementAuthProvider>
          {children}
          <NotificationProvider />
          <LoadingOverlay />
        </ManagementAuthProvider>
      </QueryProvider>
    </ErrorBoundary>
  );
}