'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AdminLayout } from '../components/layout/AdminLayout';

export default function AdminHomePage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to dashboard for authenticated users
    router.replace('/dashboard');
  }, [router]);

  return (
    <AdminLayout>
      <div className='flex items-center justify-center h-full'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4'></div>
          <p className='text-gray-600'>Loading DotMac ISP Management Platform...</p>
        </div>
      </div>
    </AdminLayout>
  );
}
