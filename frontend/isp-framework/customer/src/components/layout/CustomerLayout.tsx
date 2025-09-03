'use client';

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

interface CustomerLayoutProps {
  children: ReactNode;
}

export function CustomerLayout({ children }: CustomerLayoutProps) {
  const router = useRouter();
  const { user, logout, currentPortal, getPortalBranding } = useUniversalAuth();

  const branding = getPortalBranding();

  return (
    <UniversalNavigation
      items={NavigationPresets.customer()}
      variant='customer'
      layoutType='sidebar'
      user={UserHelper.format(user)}
      branding={
        branding
          ? {
              logo: branding.logo,
              companyName: branding.companyName || 'Customer Portal',
              primaryColor: branding.primaryColor || '#059669',
            }
          : {
              companyName: 'Customer Portal',
              primaryColor: '#059669',
            }
      }
      tenant={BrandingHelper.fromTenant(currentPortal)}
      onNavigate={NavigationHookHelpers.createNavigationHandler(router)}
      onLogout={NavigationHookHelpers.createLogoutHandler({ logout })}
    >
      {children}
    </UniversalNavigation>
  );
}
