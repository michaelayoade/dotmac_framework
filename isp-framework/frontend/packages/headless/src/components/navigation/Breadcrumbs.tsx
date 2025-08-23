/**
 * Breadcrumb navigation component for ISP platform
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useMemo } from 'react';

import { usePermissions } from '../../hooks/usePermissions';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ComponentType<{ className?: string }>;
  requiredPermissions?: string[];
  requiredRoles?: string[];
}

interface BreadcrumbsProps {
  items?: BreadcrumbItem[];
  separator?: React.ReactNode;
  maxItems?: number;
  showHome?: boolean;
  className?: string;
}

// Route-to-breadcrumb mapping for automatic generation
const ROUTE_BREADCRUMBS: Record<string, BreadcrumbItem[]> = {
  '/admin': [{ label: 'Dashboard', href: '/admin' }],
  '/admin/customers': [
    { label: 'Dashboard', href: '/admin' },
    { label: 'Customers', href: '/admin/customers', requiredPermissions: ['customers:read'] },
  ],
  '/admin/customers/create': [
    { label: 'Dashboard', href: '/admin' },
    { label: 'Customers', href: '/admin/customers', requiredPermissions: ['customers:read'] },
    { label: 'Create Customer', requiredPermissions: ['customers:create'] },
  ],
  '/admin/network': [
    { label: 'Dashboard', href: '/admin' },
    { label: 'Network', href: '/admin/network', requiredPermissions: ['network:read'] },
  ],
  '/admin/network/devices': [
    { label: 'Dashboard', href: '/admin' },
    { label: 'Network', href: '/admin/network', requiredPermissions: ['network:read'] },
    { label: 'Devices', requiredPermissions: ['devices:read'] },
  ],
  '/admin/billing': [
    { label: 'Dashboard', href: '/admin' },
    { label: 'Billing', href: '/admin/billing', requiredPermissions: ['billing:read'] },
  ],
  '/admin/support': [
    { label: 'Dashboard', href: '/admin' },
    { label: 'Support', href: '/admin/support', requiredPermissions: ['support:read'] },
  ],
  '/customer/services': [
    { label: 'Dashboard', href: '/' },
    { label: 'Services', href: '/services' },
  ],
  '/customer/billing': [
    { label: 'Dashboard', href: '/' },
    { label: 'Billing', href: '/billing' },
  ],
  '/reseller/customers': [
    { label: 'Dashboard', href: '/' },
    { label: 'Customers', href: '/customers' },
  ],
  '/reseller/territory': [
    { label: 'Dashboard', href: '/' },
    { label: 'Territory', href: '/territory' },
  ],
};

export function Breadcrumbs({
  items,
  separator = (
    <svg
      className="h-4 w-4 text-gray-400"
      fill="currentColor"
      viewBox="0 0 20 20"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
        clipRule="evenodd"
      />
    </svg>
  ),
  maxItems = 5,
  showHome = true,
  className = '',
}: BreadcrumbsProps) {
  const pathname = usePathname();
  const { getAccessibleMenuItems } = usePermissions();

  // Generate breadcrumbs automatically from pathname if no items provided
  const breadcrumbItems = useMemo(() => {
    if (items) {
      return items;
    }

    // Get breadcrumbs from route mapping
    const routeBreadcrumbs = ROUTE_BREADCRUMBS[pathname] || [];
    
    // Filter based on permissions
    const accessibleItems = getAccessibleMenuItems(
      routeBreadcrumbs.map(item => ({
        id: item.label,
        requiredPermissions: item.requiredPermissions,
        requiredRoles: item.requiredRoles,
      }))
    );

    return routeBreadcrumbs.filter((_, index) => 
      accessibleItems.some(accessible => accessible.id === routeBreadcrumbs[index].label)
    );
  }, [items, pathname, getAccessibleMenuItems]);

  // Add home breadcrumb if requested
  const allItems = useMemo(() => {
    const homeItem: BreadcrumbItem = {
      label: 'Home',
      href: '/',
      icon: ({ className }) => (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
          />
        </svg>
      ),
    };

    return showHome && breadcrumbItems.length > 0 && breadcrumbItems[0].label !== 'Home'
      ? [homeItem, ...breadcrumbItems]
      : breadcrumbItems;
  }, [breadcrumbItems, showHome]);

  // Truncate items if exceeds maxItems
  const displayItems = useMemo(() => {
    if (allItems.length <= maxItems) {
      return allItems;
    }

    const firstItem = allItems[0];
    const lastItems = allItems.slice(-2); // Always show last 2 items
    const middleCount = maxItems - 3; // Account for first item + ellipsis + last 2 items

    if (middleCount > 0) {
      const middleItems = allItems.slice(1, 1 + middleCount);
      return [firstItem, ...middleItems, { label: '...' }, ...lastItems];
    }

    return [firstItem, { label: '...' }, ...lastItems];
  }, [allItems, maxItems]);

  if (displayItems.length === 0) {
    return null;
  }

  return (
    <nav className={`flex ${className}`} aria-label="Breadcrumb">
      <ol role="list" className="flex items-center space-x-2">
        {displayItems.map((item, index) => (
          <li key={`${item.label}-${index}`} className="flex items-center">
            {index > 0 && <div className="mr-2">{separator}</div>}
            
            {item.label === '...' ? (
              <span className="text-gray-500 text-sm">...</span>
            ) : item.href ? (
              <Link
                href={item.href}
                className="flex items-center text-gray-500 text-sm transition-colors hover:text-gray-700"
              >
                {item.icon && (
                  <item.icon className="mr-1.5 h-4 w-4 flex-shrink-0" />
                )}
                {item.label}
              </Link>
            ) : (
              <span className="flex items-center font-medium text-gray-900 text-sm">
                {item.icon && (
                  <item.icon className="mr-1.5 h-4 w-4 flex-shrink-0" />
                )}
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

// Higher-order component to automatically add breadcrumbs to pages
export function withBreadcrumbs<P extends object>(
  Component: React.ComponentType<P>,
  breadcrumbItems?: BreadcrumbItem[]
) {
  return function ComponentWithBreadcrumbs(props: P) {
    return (
      <div>
        <div className="mb-6">
          <Breadcrumbs items={breadcrumbItems} />
        </div>
        <Component {...props} />
      </div>
    );
  };
}

// Utility hook for managing breadcrumbs
export function useBreadcrumbs() {
  const pathname = usePathname();
  const { getAccessibleMenuItems } = usePermissions();

  const getBreadcrumbs = (customItems?: BreadcrumbItem[]) => {
    if (customItems) {
      return customItems;
    }

    const routeBreadcrumbs = ROUTE_BREADCRUMBS[pathname] || [];
    const accessibleItems = getAccessibleMenuItems(
      routeBreadcrumbs.map(item => ({
        id: item.label,
        requiredPermissions: item.requiredPermissions,
        requiredRoles: item.requiredRoles,
      }))
    );

    return routeBreadcrumbs.filter((_, index) => 
      accessibleItems.some(accessible => accessible.id === routeBreadcrumbs[index].label)
    );
  };

  const addBreadcrumb = (item: BreadcrumbItem) => {
    const currentBreadcrumbs = getBreadcrumbs();
    return [...currentBreadcrumbs, item];
  };

  return {
    getBreadcrumbs,
    addBreadcrumb,
    currentPath: pathname,
  };
}