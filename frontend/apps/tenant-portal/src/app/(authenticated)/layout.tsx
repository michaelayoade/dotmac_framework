'use client';

import { TenantLayout } from '@/components/layout/TenantLayout';
import { useTenantAuth } from '@/components/auth/TenantAuthProviderNew';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useTenantAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tenant-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading your tenant portal...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect to login
  }

  return (
    <TenantLayout>
      {children}
    </TenantLayout>
  );
}
