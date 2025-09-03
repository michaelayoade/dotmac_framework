'use client';

import {
  UniversalNavigation,
  NavigationPresets,
  UserHelper,
  NavigationHookHelpers,
} from '@dotmac/navigation-system';
import { useUniversalAuth } from '@dotmac/headless';
import { useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import type { ReactNode } from 'react';

interface AdminLayoutProps {
  children: ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  const router = useRouter();
  const { user, logout } = useUniversalAuth();

  return (
    <ProtectedRoute requireMasterAdmin>
      <UniversalNavigation
        items={NavigationPresets.management()}
        variant='management'
        layoutType='sidebar'
        user={UserHelper.format(user)}
        branding={{
          companyName: 'DotMac Management',
          primaryColor: '#EA580C',
        }}
        onNavigate={NavigationHookHelpers.createNavigationHandler(router)}
        onLogout={NavigationHookHelpers.createLogoutHandler({ logout })}
      >
        {children}
      </UniversalNavigation>
    </ProtectedRoute>
  );
}
