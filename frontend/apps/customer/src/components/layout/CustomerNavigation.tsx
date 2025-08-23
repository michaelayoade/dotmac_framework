'use client';

import { EnhancedTabNavigation, MobileNavigation } from '@dotmac/primitives';
import {
  CreditCard,
  FileText,
  LayoutDashboard,
  MessageSquare,
  Settings,
  TrendingUp,
  Wifi,
} from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import type React from 'react';

interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const navItems: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
  },
  {
    id: 'services',
    label: 'My Services',
    href: '/services',
    icon: Wifi,
  },
  {
    id: 'usage',
    label: 'Usage & Performance',
    href: '/usage',
    icon: TrendingUp,
  },
  {
    id: 'billing',
    label: 'Billing & Payments',
    href: '/billing',
    icon: CreditCard,
  },
  {
    id: 'support',
    label: 'Support',
    href: '/support',
    icon: MessageSquare,
    badge: '1',
  },
  {
    id: 'documents',
    label: 'Documents',
    href: '/documents',
    icon: FileText,
  },
  {
    id: 'settings',
    label: 'Account Settings',
    href: '/settings',
    icon: Settings,
  },
];

export function CustomerNavigation() {
  const pathname = usePathname();
  const router = useRouter();

  const handleNavigate = (href: string) => {
    router.push(href);
  };

  return (
    <nav className='customer-nav'>
      <div className='container mx-auto px-4'>
        {/* Desktop and tablet: Enhanced tab navigation */}
        <div className='hidden sm:block'>
          <EnhancedTabNavigation
            items={navItems}
            currentPath={pathname}
            onNavigate={handleNavigate}
          />
        </div>

        {/* Mobile: Drawer navigation */}
        <div className='flex items-center justify-between sm:hidden'>
          <div className='flex-1'>
            <h1 className='font-semibold text-gray-900 text-lg'>
              {navItems.find((item) => item.href === pathname)?.label || 'Dashboard'}
            </h1>
          </div>
          <MobileNavigation
            items={navItems}
            currentPath={pathname}
            onNavigate={handleNavigate}
            variant='drawer'
          />
        </div>
      </div>
    </nav>
  );
}
