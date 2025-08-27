'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import type { ReactNode } from 'react';
import { useAuthToken } from '../../hooks/useSSRSafeStorage';

interface ProtectedLayoutProps {
  children: ReactNode;
}

export default function ProtectedLayout({ children }: ProtectedLayoutProps) {
  const router = useRouter();
  const [authToken, , tokenLoading] = useAuthToken();

  useEffect(() => {
    if (tokenLoading) return; // Wait for token check
    
    if (!authToken) {
      // Redirect unauthenticated users to login
      router.replace('/login');
    }
  }, [router, authToken, tokenLoading]);

  // Show loading while checking authentication
  if (tokenLoading) {
    return (
      <div className='flex items-center justify-center h-screen bg-gray-50'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4'></div>
          <p className='text-gray-600'>Authenticating...</p>
        </div>
      </div>
    );
  }

  // Don't render children if not authenticated (redirect will happen)
  if (!authToken) {
    return null;
  }

  return <>{children}</>;
}
