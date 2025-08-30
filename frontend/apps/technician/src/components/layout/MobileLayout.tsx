'use client';

import {
  UniversalNavigation,
  NavigationPresets,
  UserHelper,
  BrandingHelper,
  NavigationHookHelpers
} from '@dotmac/navigation-system';
import { useUniversalAuth } from '@dotmac/headless';
import { MobileLayout as MobileLayoutBase, useMobile } from '@dotmac/mobile';
import { useRouter } from 'next/navigation';
import { ReactNode } from 'react';

interface MobileLayoutProps {
  children: ReactNode;
  showHeader?: boolean;
  showNavigation?: boolean;
  headerTitle?: string;
  className?: string;
}

export function MobileLayout({
  children,
  showHeader = true,
  showNavigation = true,
  headerTitle,
  className = '',
}: MobileLayoutProps) {
  const router = useRouter();
  const { user, logout, currentPortal, getPortalBranding } = useUniversalAuth();
  const { isMobile, offline, pwa } = useMobile();

  const branding = getPortalBranding();

  // Enhanced mobile layout with offline indicators
  const enhancedChildren = (
    <>
      {/* Offline Indicator */}
      {!offline.isOnline && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-amber-500 text-white px-4 py-2 text-sm text-center font-medium">
          Offline Mode - Changes will sync when online ({offline.pendingOperations} pending)
        </div>
      )}

      {/* PWA Update Banner */}
      {pwa.updateAvailable && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-blue-600 text-white px-4 py-2 text-sm text-center font-medium">
          App update available
          <button
            className="ml-2 px-2 py-1 bg-white text-blue-600 rounded text-xs font-semibold"
            onClick={pwa.updateApp}
          >
            Update
          </button>
        </div>
      )}

      {/* Main Content */}
      {children}
    </>
  );

  // Use mobile-optimized layout for mobile devices
  if (isMobile) {
    return (
      <MobileLayoutBase
        showHeader={showHeader}
        showNavigation={showNavigation}
        safeArea={true}
        backgroundColor="bg-gray-50"
        className={className}
        header={
          showHeader && (
            <div className="bg-white border-b border-gray-200 px-4 py-3">
              <h1 className="text-lg font-semibold text-gray-900">
                {headerTitle || branding?.companyName || 'Technician App'}
              </h1>
            </div>
          )
        }
        navigation={
          showNavigation && (
            <nav className="bg-white border-t border-gray-200">
              <div className="flex justify-around py-2">
                {NavigationPresets.technician().map((item) => (
                  <button
                    key={item.id}
                    className="flex flex-col items-center px-3 py-2 text-gray-600 hover:text-blue-600"
                    onClick={() => router.push(item.path || '/')}
                  >
                    {item.icon && <span className="mb-1">{item.icon}</span>}
                    <span className="text-xs">{item.label}</span>
                  </button>
                ))}
              </div>
            </nav>
          )
        }
      >
        {enhancedChildren}
      </MobileLayoutBase>
    );
  }

  // Fallback to desktop navigation for larger screens
  return (
    <UniversalNavigation
      items={NavigationPresets.technician()}
      variant="technician"
      layoutType="hybrid"
      user={UserHelper.format(user)}
      branding={branding ? {
        logo: branding.logo,
        companyName: branding.companyName || 'Technician App',
        primaryColor: branding.primaryColor || '#F59E0B'
      } : {
        companyName: 'Technician App',
        primaryColor: '#F59E0B'
      }}
      tenant={BrandingHelper.fromTenant(currentPortal)}
      onNavigate={NavigationHookHelpers.createNavigationHandler(router)}
      onLogout={NavigationHookHelpers.createLogoutHandler({ logout })}
      className={className}
    >
      {enhancedChildren}
    </UniversalNavigation>
  );
}
