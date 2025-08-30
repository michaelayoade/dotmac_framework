'use client';

import {
  UniversalNavigation,
  NavigationPresets,
  UserHelper,
  BrandingHelper,
  NavigationHookHelpers
} from '@dotmac/navigation-system';
import { useUniversalAuth } from '@dotmac/headless';
import { useRouter } from 'next/navigation';
import type { ReactNode } from 'react';

interface ResellerLayoutProps {
  children: ReactNode;
}

export function ResellerLayout({ children }: ResellerLayoutProps) {
  const router = useRouter();
  const { user, logout, currentPortal, getPortalBranding } = useUniversalAuth();

  const branding = getPortalBranding();

  return (
    <UniversalNavigation
      items={NavigationPresets.reseller()}
      variant="reseller"
      layoutType="sidebar"
      user={UserHelper.format(user)}
      branding={branding ? {
        logo: branding.logo,
        companyName: branding.companyName || 'Reseller Portal',
        primaryColor: branding.primaryColor || '#9333EA'
      } : {
        companyName: 'Reseller Portal',
        primaryColor: '#9333EA'
      }}
      tenant={BrandingHelper.fromTenant(currentPortal)}
      onNavigate={NavigationHookHelpers.createNavigationHandler(router)}
      onLogout={NavigationHookHelpers.createLogoutHandler({ logout })}
    >
      {children}
    </UniversalNavigation>
  );
}
