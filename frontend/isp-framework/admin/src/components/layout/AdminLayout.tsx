'use client';

import { ErrorBoundary } from '@dotmac/providers/error';
import {
  UniversalNavigation,
  NavigationPresets,
  UserHelper,
  BrandingHelper,
  NavigationHookHelpers,
} from '@dotmac/navigation-system';
import { useUniversalAuth } from '@dotmac/headless';
import { useRouter } from 'next/navigation';
import type { ReactNode } from 'react';

interface AdminLayoutProps {
  children: ReactNode;
}

function AdminLayout({ children }: AdminLayoutProps) {
  const router = useRouter();
  const { user, logout, currentPortal } = useUniversalAuth();

  return (
    <ErrorBoundary level='section'>
      <UniversalNavigation
        items={NavigationPresets.admin()}
        variant='admin'
        layoutType='sidebar'
        user={UserHelper.format(user)}
        branding={
          BrandingHelper.fromTenant(currentPortal) || {
            companyName: 'DotMac Admin',
            primaryColor: '#3B82F6',
          }
        }
        onNavigate={NavigationHookHelpers.createNavigationHandler(router)}
        onLogout={NavigationHookHelpers.createLogoutHandler({ logout })}
      >
        <ErrorBoundary level='section'>{children}</ErrorBoundary>
      </UniversalNavigation>
    </ErrorBoundary>
  );
}

export default AdminLayout;
