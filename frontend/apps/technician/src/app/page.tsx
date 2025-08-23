'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { MobileLayout } from '../components/layout/MobileLayout';

export default function TechnicianHomePage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to work orders for field technicians
    router.replace('/work-orders');
  }, [router]);

  return (
    <MobileLayout headerTitle='DotMac Field Service'>
      <div className='flex flex-col items-center justify-center h-full'>
        <div className='text-center p-6'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto mb-4'></div>
          <p className='text-gray-600'>Loading Field Service Portal...</p>
          <p className='text-sm text-gray-500 mt-2'>Redirecting to work orders...</p>
        </div>
      </div>
    </MobileLayout>
  );
}
