'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthToken } from '../hooks/useSSRSafeStorage';

export default function AdminHomePage() {
  const router = useRouter();
  const [authToken, , tokenLoading] = useAuthToken();

  useEffect(() => {
    if (tokenLoading) return; // Wait for token check

    if (authToken) {
      // Redirect authenticated users to dashboard
      router.replace('/dashboard');
    } else {
      // Redirect unauthenticated users to login
      router.replace('/login');
    }
  }, [router, authToken, tokenLoading]);

  return (
    <div className='flex items-center justify-center h-screen bg-gray-50'>
      <div className='text-center'>
        <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4'></div>
        <p className='text-gray-600'>Loading DotMac ISP Management Platform...</p>
      </div>
    </div>
  );
}
