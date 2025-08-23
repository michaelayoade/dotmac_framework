/**
 * Main navigation menu component for ISP platform
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

import { usePermissions } from '../../hooks/usePermissions';
import { usePortalAuth } from '../../hooks/usePortalAuth';

export interface NavigationItem {
  id: string;
  label: string;
  href?: string;
  icon?: React.ComponentType<{ className?: string }>;
  children?: NavigationItem[];
  requiredPermissions?: string[];
  requiredRoles?: string[];
  requiredFeatures?: string[];
  badge?: string | number;
  external?: boolean;
  onClick?: () => void;
}

interface NavigationMenuProps {
  items: NavigationItem[];
  orientation?: 'horizontal' | 'vertical';
  variant?: 'sidebar' | 'topbar' | 'mobile';
  collapsible?: boolean;
  className?: string;
  onItemClick?: (item: NavigationItem) => void;
}

// Portal-specific navigation configurations
const PORTAL_NAVIGATION: Record<string, NavigationItem[]> = {
  admin: [
    {
      id: 'dashboard',
      label: 'Dashboard',
      href: '/admin',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      ),
    },
    {
      id: 'customers',
      label: 'Customers',
      requiredPermissions: ['customers:read'],
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      ),
      children: [
        { id: 'customer-list', label: 'Customer List', href: '/admin/customers' },
        { id: 'customer-create', label: 'Add Customer', href: '/admin/customers/create', requiredPermissions: ['customers:create'] },
        { id: 'customer-import', label: 'Import Customers', href: '/admin/customers/import', requiredPermissions: ['customers:create'] },
      ],
    },
    {
      id: 'network',
      label: 'Network',
      requiredPermissions: ['network:read'],
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
        </svg>
      ),
      children: [
        { id: 'network-overview', label: 'Network Overview', href: '/admin/network' },
        { id: 'network-devices', label: 'Devices', href: '/admin/network/devices' },
        { id: 'network-monitoring', label: 'Monitoring', href: '/admin/network/monitoring' },
        { id: 'network-topology', label: 'Topology', href: '/admin/network/topology' },
      ],
    },
    {
      id: 'billing',
      label: 'Billing',
      requiredPermissions: ['billing:read'],
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      children: [
        { id: 'billing-overview', label: 'Billing Overview', href: '/admin/billing' },
        { id: 'billing-invoices', label: 'Invoices', href: '/admin/billing/invoices' },
        { id: 'billing-payments', label: 'Payments', href: '/admin/billing/payments' },
        { id: 'billing-tariffs', label: 'Tariffs', href: '/admin/billing/tariffs' },
      ],
    },
    {
      id: 'support',
      label: 'Support',
      requiredPermissions: ['support:read'],
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192L5.636 18.364M12 2.636a9.364 9.364 0 000 18.728 9.364 9.364 0 000-18.728z" />
        </svg>
      ),
      children: [
        { id: 'support-tickets', label: 'Support Tickets', href: '/admin/support' },
        { id: 'support-knowledge', label: 'Knowledge Base', href: '/admin/support/knowledge' },
      ],
    },
    {
      id: 'analytics',
      label: 'Analytics',
      requiredPermissions: ['analytics:read'],
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      href: '/admin/analytics',
    },
    {
      id: 'settings',
      label: 'Settings',
      requiredPermissions: ['settings:read'],
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
      href: '/admin/settings',
    },
  ],
  customer: [
    {
      id: 'dashboard',
      label: 'Dashboard',
      href: '/',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
    {
      id: 'services',
      label: 'Services',
      href: '/services',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
        </svg>
      ),
    },
    {
      id: 'usage',
      label: 'Usage',
      href: '/usage',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
    {
      id: 'billing',
      label: 'Billing',
      href: '/billing',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      id: 'support',
      label: 'Support',
      href: '/support',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192L5.636 18.364M12 2.636a9.364 9.364 0 000 18.728 9.364 9.364 0 000-18.728z" />
        </svg>
      ),
    },
    {
      id: 'documents',
      label: 'Documents',
      href: '/documents',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
  ],
  reseller: [
    {
      id: 'dashboard',
      label: 'Dashboard',
      href: '/',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      ),
    },
    {
      id: 'customers',
      label: 'Customers',
      href: '/customers',
      requiredPermissions: ['customers:read'],
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      ),
    },
    {
      id: 'sales',
      label: 'Sales',
      href: '/sales',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
      ),
    },
    {
      id: 'commissions',
      label: 'Commissions',
      href: '/commissions',
      requiredPermissions: ['commissions:read'],
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      id: 'territory',
      label: 'Territory',
      href: '/territory',
      requiredPermissions: ['territory:read'],
      requiredRoles: ['reseller-admin'],
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    },
  ],
};

export function NavigationMenu({
  items,
  orientation = 'vertical',
  variant = 'sidebar',
  collapsible = false,
  className = '',
  onItemClick,
}: NavigationMenuProps) {
  const pathname = usePathname();
  const { currentPortal } = usePortalAuth();
  const { getAccessibleMenuItems } = usePermissions();

  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Use portal-specific navigation if no items provided
  const navigationItems = items || (currentPortal ? PORTAL_NAVIGATION[currentPortal.type] || [] : []);

  // Filter items based on permissions
  const accessibleItems = getAccessibleMenuItems(navigationItems);

  const toggleExpanded = (itemId: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId);
    } else {
      newExpanded.add(itemId);
    }
    setExpandedItems(newExpanded);
  };

  const isActiveItem = (item: NavigationItem): boolean => {
    if (item.href && pathname === item.href) {
      return true;
    }
    if (item.children) {
      return item.children.some(child => child.href === pathname);
    }
    return false;
  };

  const renderNavigationItem = (item: NavigationItem, level = 0) => {
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.has(item.id);
    const isActive = isActiveItem(item);

    const itemClasses = `
      group flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors
      ${level > 0 ? 'ml-4' : ''}
      ${isActive 
        ? 'bg-blue-100 text-blue-900' 
        : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
      }
      ${variant === 'mobile' ? 'w-full' : ''}
    `;

    const handleClick = () => {
      if (hasChildren) {
        toggleExpanded(item.id);
      }
      if (item.onClick) {
        item.onClick();
      }
      if (onItemClick) {
        onItemClick(item);
      }
    };

    const content = (
      <>
        <div className="flex items-center">
          {item.icon && !isCollapsed && (
            <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
          )}
          {!isCollapsed && (
            <>
              <span className="truncate">{item.label}</span>
              {item.badge && (
                <span className="ml-2 inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                  {item.badge}
                </span>
              )}
            </>
          )}
        </div>
        {hasChildren && !isCollapsed && (
          <svg
            className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        )}
      </>
    );

    return (
      <li key={item.id}>
        {item.href && !hasChildren ? (
          <Link href={item.href} className={itemClasses} onClick={handleClick}>
            {content}
          </Link>
        ) : (
          <button
            type="button"
            className={itemClasses}
            onClick={handleClick}
          >
            {content}
          </button>
        )}

        {hasChildren && isExpanded && !isCollapsed && (
          <ul className="mt-1 space-y-1">
            {item.children!.map(child => renderNavigationItem(child, level + 1))}
          </ul>
        )}
      </li>
    );
  };

  const baseClasses = `
    ${orientation === 'horizontal' ? 'flex flex-row space-x-1' : 'space-y-1'}
    ${variant === 'mobile' ? 'px-2 pb-3 pt-2' : ''}
    ${className}
  `;

  return (
    <nav className={baseClasses}>
      {collapsible && variant === 'sidebar' && (
        <div className="mb-4 flex items-center justify-between">
          <button
            type="button"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="rounded-lg p-2 text-gray-500 hover:bg-gray-100"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d={isCollapsed ? "M4 6h16M4 12h16M4 18h16" : "M6 18L18 6M6 6l12 12"} 
              />
            </svg>
          </button>
        </div>
      )}

      <ul className={orientation === 'horizontal' ? 'flex space-x-1' : 'space-y-1'}>
        {accessibleItems.map(item => {
          const navItem = navigationItems.find(nav => nav.id === item.id);
          return navItem ? renderNavigationItem(navItem) : null;
        })}
      </ul>
    </nav>
  );
}

// Utility hook for navigation state
export function useNavigationMenu() {
  const pathname = usePathname();
  const { currentPortal } = usePortalAuth();

  const getNavigationItems = (portalType?: string) => {
    const type = portalType || currentPortal?.type;
    return type ? PORTAL_NAVIGATION[type] || [] : [];
  };

  const findActiveItem = (items: NavigationItem[]): NavigationItem | null => {
    for (const item of items) {
      if (item.href === pathname) {
        return item;
      }
      if (item.children) {
        const activeChild = findActiveItem(item.children);
        if (activeChild) {
          return activeChild;
        }
      }
    }
    return null;
  };

  const getActiveItem = () => {
    const items = getNavigationItems();
    return findActiveItem(items);
  };

  return {
    getNavigationItems,
    getActiveItem,
    currentPath: pathname,
    currentPortal: currentPortal?.type,
  };
}