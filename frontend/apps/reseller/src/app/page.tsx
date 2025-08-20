'use client';

import { usePortalAuth } from '@dotmac/headless';

import { ResellerLogin } from '../components/auth/ResellerLogin';
import { ResellerDashboard } from '../components/dashboard/ResellerDashboard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export default function ResellerHomePage() {
  const { user, isLoading } = usePortalAuth();

  if (isLoading) {
    return (
      <div className='flex min-h-screen items-center justify-center'>
        <LoadingSpinner size='lg' />
      </div>
    );
  }

  if (!user) {
    return <ResellerLogin />;
  }

  return <ResellerDashboard />;
}
