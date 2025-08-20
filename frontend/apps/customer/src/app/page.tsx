'use client';

import { useAuth } from '@dotmac/headless';

import { CustomerLogin } from '../components/auth/CustomerLogin';
import { CustomerDashboard } from '../components/dashboard/CustomerDashboard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export default function CustomerHomePage() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className='flex min-h-screen items-center justify-center'>
        <LoadingSpinner size='lg' />
      </div>
    );
  }

  if (!user) {
    return <CustomerLogin />;
  }

  return <CustomerDashboard />;
}
