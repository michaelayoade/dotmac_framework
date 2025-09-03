'use client';

import { IntegratedManagementLayout } from '@/components/layout/IntegratedManagementLayout';
import { useAuth } from '@dotmac/auth';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className='min-h-screen flex items-center justify-center bg-gray-50'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-management-600 mx-auto mb-4' />
          <p className='text-gray-600'>Loading management portal...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect to login
  }

  return <IntegratedManagementLayout>{children}</IntegratedManagementLayout>;
}
