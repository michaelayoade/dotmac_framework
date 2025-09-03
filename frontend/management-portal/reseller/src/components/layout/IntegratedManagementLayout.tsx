'use client';

import { UniversalLayout } from '@dotmac/primitives';
import {
  UniversalNavigation,
  NavigationPresets,
  NavigationHookHelpers,
} from '@dotmac/navigation-system';
import { useAuth } from '@dotmac/auth';
import { useRouter } from 'next/navigation';
import { ReactNode } from 'react';

interface IntegratedManagementLayoutProps {
  children: ReactNode;
}

export function IntegratedManagementLayout({ children }: IntegratedManagementLayoutProps) {
  const { user, logout, isLoading } = useAuth();
  const router = useRouter();

  // Get management navigation items
  const navigationItems = NavigationPresets.management();

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

  return (
    <UniversalLayout
      variant='management'
      navigation={navigationItems}
      user={{
        id: user?.id || '',
        name: user?.name || '',
        email: user?.email || '',
        role: user?.role || '',
        avatar: user?.avatar,
      }}
      tenant={{
        id: 'management',
        name: 'Management Portal',
      }}
      branding={{
        logo: '/images/dotmac-logo.svg',
        companyName: 'DotMac Management',
        primaryColor: '#4f46e5',
      }}
      onLogout={async () => await logout()}
      showSidebar={true}
      sidebarCollapsible={true}
      layoutType='dashboard'
      headerActions={[]}
    >
      {children}
    </UniversalLayout>
  );
}
