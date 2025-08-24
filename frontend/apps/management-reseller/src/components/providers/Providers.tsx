'use client';

import { ManagementAuthProvider } from '@/components/auth/ManagementAuthProvider';

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <ManagementAuthProvider>
      {children}
    </ManagementAuthProvider>
  );
}