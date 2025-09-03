'use client';

import { useEffect } from 'react';
import { LayoutDashboard, Settings, CreditCard, Users, BarChart3, HelpCircle } from 'lucide-react';
import { useTenantAuth } from '@/components/auth/TenantAuthProviderNew';
import { UniversalLayout } from '@dotmac/primitives';

const navigation = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    id: 'settings',
    label: 'Settings',
    href: '/settings',
    icon: Settings,
  },
  {
    id: 'billing',
    label: 'Billing',
    href: '/billing',
    icon: CreditCard,
  },
  {
    id: 'users',
    label: 'Users',
    href: '/users',
    icon: Users,
  },
  {
    id: 'analytics',
    label: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
  },
  {
    id: 'support',
    label: 'Support',
    href: '/support',
    icon: HelpCircle,
    badge: 2,
  },
];

interface TenantLayoutProps {
  children: React.ReactNode;
}

export function TenantLayout({ children }: TenantLayoutProps) {
  const { user, tenant, logout, isLoading } = useTenantAuth();

  // Apply tenant branding
  useEffect(() => {
    if (tenant?.primary_color) {
      document.documentElement.style.setProperty('--tenant-primary', tenant.primary_color);
    }

    if (tenant?.display_name) {
      document.title = `${tenant.display_name} - Tenant Portal`;
    }
  }, [tenant]);

  if (isLoading) {
    return (
      <div className='min-h-screen flex items-center justify-center'>
        <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600' />
      </div>
    );
  }

  return (
    <UniversalLayout
      variant='customer'
      user={
        user
          ? {
              id: user.id,
              name: user.name,
              email: user.email,
              avatar: user.metadata?.avatar,
              role: user.role,
            }
          : undefined
      }
      branding={
        tenant
          ? {
              companyName: tenant.display_name || tenant.name,
              primaryColor: tenant.primary_color || '#3b82f6',
              logo: tenant.logo_url,
            }
          : {
              companyName: 'Tenant Portal',
              primaryColor: '#3b82f6',
            }
      }
      tenant={
        tenant
          ? {
              id: tenant.id,
              name: tenant.display_name || tenant.name,
            }
          : undefined
      }
      navigation={navigation}
      onLogout={logout}
      layoutType='dashboard'
      showSidebar={true}
      sidebarCollapsible={true}
      showHeader={true}
      showNotifications={true}
      notificationBadge={3}
      className='min-h-screen'
    >
      {children}
    </UniversalLayout>
  );
}
