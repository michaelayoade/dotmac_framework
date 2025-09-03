'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { ResellerLayout } from '../components/layout/ResellerLayout';

export default function ResellerHomePage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to dashboard for authenticated users
    router.replace('/dashboard');
  }, [router]);

  return (
    <ResellerLayout>
      <div className='flex items-center justify-center h-full'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4'></div>
          <p className='text-gray-600'>Loading DotMac Reseller Management Platform...</p>
        </div>
      </div>
    </ResellerLayout>
  );
}
