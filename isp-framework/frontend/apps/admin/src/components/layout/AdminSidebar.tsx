'use client';

import { usePermissions } from '@dotmac/headless';
import { ResponsiveSidebar } from '@dotmac/primitives/navigation/ResponsiveSidebar';
import {
  BarChart3,
  CreditCard,
  FileText,
  FolderOpen,
  HeadphonesIcon,
  LayoutDashboard,
  Network,
  Plug,
  Server,
  Settings,
  Shield,
  TrendingUp,
  Users,
  Workflow,
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

interface MenuGroup {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string | undefined }>;
  items: MenuItem[];
  defaultExpanded?: boolean;
}

const menuGroups: MenuGroup[] = [
  // Always visible dashboard
  {
    id: 'overview',
    label: 'Overview',
    icon: LayoutDashboard,
    defaultExpanded: true,
    items: [
      {
        id: 'dashboard',
        label: 'Dashboard',
        href: '/dashboard',
        icon: LayoutDashboard,
      },
    ],
  },
  // CustomerOps - Customer-facing operations
  {
    id: 'customer-ops',
    label: 'Customer Operations',
    icon: Users,
    defaultExpanded: false,
    items: [
      {
        id: 'customers',
        label: 'Customers',
        href: '/customers',
        icon: Users,
        requiredPermissions: ['customers:read'],
      },
      {
        id: 'support',
        label: 'Support',
        href: '/support',
        icon: HeadphonesIcon,
        requiredPermissions: ['support:read'],
        badge: '3',
      },
      {
        id: 'billing',
        label: 'Billing',
        href: '/billing',
        icon: CreditCard,
        requiredPermissions: ['billing:read'],
      },
    ],
  },
  // NetworkOps - Network infrastructure and monitoring
  {
    id: 'network-ops',
    label: 'Network Operations',
    icon: Network,
    defaultExpanded: false,
    items: [
      {
        id: 'network',
        label: 'Network',
        href: '/network',
        icon: Network,
        requiredPermissions: ['network:read'],
      },
      {
        id: 'monitoring',
        label: 'Monitoring',
        href: '/monitoring',
        icon: Server,
        requiredPermissions: ['monitoring:read'],
      },
    ],
  },
  // BusinessOps - Analytics and operational workflows
  {
    id: 'business-ops',
    label: 'Business Operations',
    icon: TrendingUp,
    defaultExpanded: false,
    items: [
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
    ],
  },
  // SystemOps - System administration and security
  {
    id: 'system-ops',
    label: 'System Operations',
    icon: Shield,
    defaultExpanded: false,
    items: [
      {
        id: 'security',
        label: 'Security',
        href: '/security',
        icon: Shield,
        requiredPermissions: ['security:read'],
      },
      {
        id: 'audit',
        label: 'Audit Logs',
        href: '/audit',
        icon: FileText,
        requiredPermissions: ['audit:read'],
      },
      {
        id: 'plugins',
        label: 'Plugins',
        href: '/plugins',
        icon: Plug,
        requiredPermissions: ['plugins:manage'],
      },
      {
        id: 'settings',
        label: 'Settings',
        href: '/settings',
        icon: Settings,
        requiredPermissions: ['settings:read'],
      },
    ],
  },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { getAccessibleMenuItems } = usePermissions();

  // Transform groups to flat items for permission filtering, then regroup
  const accessibleGroups = menuGroups.map(group => ({
    ...group,
    items: getAccessibleMenuItems(group.items)
  })).filter(group => group.items.length > 0); // Only show groups with accessible items

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
      groups={accessibleGroups}
      currentPath={pathname}
      onNavigate={handleNavigate}
      title='Administration'
      footer={systemStatusFooter}
      collapsible={true}
      defaultCollapsed={false}
      className='admin-sidebar'
      groupedLayout={true}
    />
  );
}
