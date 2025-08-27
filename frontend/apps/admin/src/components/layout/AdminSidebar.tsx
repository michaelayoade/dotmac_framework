'use client';

import { usePermissions } from '@dotmac/headless';
import { ResponsiveSidebar } from '@dotmac/primitives/navigation/ResponsiveSidebar';
import {
  BarChart3,
  CreditCard,
  FileText,
  HeadphonesIcon,
  LayoutDashboard,
  Network,
  Settings,
  Shield,
  Users,
  Workflow,
  Activity,
} from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import type React from 'react';

interface MenuItem {
  id: string;
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string | undefined }>;
  requiredPermissions?: string[];
  badge?: string;
}

const menuItems: MenuItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
  },
  {
    id: 'customers',
    label: 'Customers',
    href: '/customers',
    icon: Users,
    requiredPermissions: ['customers:read'],
  },
  {
    id: 'network',
    label: 'Network',
    href: '/network',
    icon: Network,
    requiredPermissions: ['network:read'],
  },
  {
    id: 'billing',
    label: 'Billing',
    href: '/billing',
    icon: CreditCard,
    requiredPermissions: ['billing:read'],
  },
  {
    id: 'helpdesk',
    label: 'Helpdesk',
    href: '/helpdesk',
    icon: HeadphonesIcon,
    requiredPermissions: ['support:read'],
    badge: '3',
  },
  {
    id: 'analytics',
    label: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
    requiredPermissions: ['analytics:read'],
  },
  {
    id: 'workflows',
    label: 'Workflows',
    href: '/workflows',
    icon: Workflow,
    requiredPermissions: ['workflows:read'],
  },
  {
    id: 'audit',
    label: 'Audit Logs',
    href: '/audit',
    icon: FileText,
    requiredPermissions: ['audit:read'],
  },
  {
    id: 'security',
    label: 'Security',
    href: '/security',
    icon: Shield,
    requiredPermissions: ['security:read'],
  },
  {
    id: 'gateway-status',
    label: 'Gateway Status',
    href: '/gateway-status',
    icon: Activity,
    requiredPermissions: ['admin', 'system.monitoring'],
  },
  {
    id: 'settings',
    label: 'Settings',
    href: '/settings',
    icon: Settings,
    requiredPermissions: ['settings:read'],
  },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { getAccessibleMenuItems } = usePermissions();

  const accessibleItems = getAccessibleMenuItems(menuItems);

  const handleNavigate = (href: string) => {
    router.push(href);
  };

  const systemStatusFooter = (
    <div className='rounded-lg bg-gray-50 p-4'>
      <div className='flex items-center'>
        <div className='status-indicator status-online mr-2' />
        <span className='font-medium text-gray-900 text-sm'>System Status</span>
      </div>
      <p className='mt-1 text-gray-500 text-xs'>All services operational</p>
    </div>
  );

  return (
    <ResponsiveSidebar
      items={accessibleItems}
      currentPath={pathname}
      onNavigate={handleNavigate}
      title='Administration'
      footer={systemStatusFooter}
      collapsible={true}
      defaultCollapsed={false}
      className='admin-sidebar'
    />
  );
}
