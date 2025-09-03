'use client';

import {
  Home,
  Users,
  CreditCard,
  Cloud,
  Puzzle,
  BarChart,
  Settings,
  AlertTriangle,
  Network,
  Package,
  GitBranch,
  Monitor,
  Server,
  Activity,
  FileText,
  Shield,
  ShieldAlert,
} from 'lucide-react';
import { NavigationItem } from '../layout/PortalSidebar';

/**
 * Management Portal Navigation Configuration
 * Includes new packages: Network, Assets, Journey Orchestration
 */
export const managementNavigation: NavigationItem[] = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: Home,
  },
  {
    name: 'Tenants',
    href: '/tenants',
    icon: Users,
  },
  {
    name: 'Billing',
    href: '/billing',
    icon: CreditCard,
  },
  {
    name: 'Infrastructure',
    href: '/infrastructure',
    icon: Cloud,
    children: [
      {
        name: 'Deployments',
        href: '/infrastructure/deployments',
        icon: Server,
      },
      {
        name: 'Monitoring',
        href: '/infrastructure/monitoring',
        icon: Monitor,
      },
    ],
  },
  {
    name: 'Network',
    href: '/network',
    icon: Network,
    children: [
      {
        name: 'Topology',
        href: '/network/topology',
        icon: GitBranch,
      },
      {
        name: 'Devices',
        href: '/network/devices',
        icon: Server,
      },
      {
        name: 'Monitoring',
        href: '/network/monitoring',
        icon: Activity,
      },
    ],
  },
  {
    name: 'Assets',
    href: '/assets',
    icon: Package,
    children: [
      {
        name: 'Inventory',
        href: '/assets/inventory',
        icon: Package,
      },
      {
        name: 'Maintenance',
        href: '/assets/maintenance',
        icon: Settings,
      },
      {
        name: 'Lifecycle',
        href: '/assets/lifecycle',
        icon: BarChart,
      },
    ],
  },
  {
    name: 'Customer Journeys',
    href: '/journeys',
    icon: GitBranch,
    children: [
      {
        name: 'Active Journeys',
        href: '/journeys/active',
        icon: Activity,
      },
      {
        name: 'Analytics',
        href: '/journeys/analytics',
        icon: BarChart,
      },
      {
        name: 'Templates',
        href: '/journeys/templates',
        icon: Settings,
      },
    ],
  },
  {
    name: 'Plugins',
    href: '/plugins',
    icon: Puzzle,
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: BarChart,
  },
  {
    name: 'Security & Audit',
    href: '/security',
    icon: Shield,
    children: [
      {
        name: 'Security Dashboard',
        href: '/security/dashboard',
        icon: Shield,
      },
      {
        name: 'Incident Response',
        href: '/security/incidents',
        icon: ShieldAlert,
      },
      {
        name: 'Audit Trail',
        href: '/security/audit',
        icon: FileText,
      },
    ],
  },
  {
    name: 'System Health',
    href: '/monitoring',
    icon: AlertTriangle,
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];

/**
 * Reseller Portal Navigation
 */
export const resellerNavigation: NavigationItem[] = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: Home,
  },
  {
    name: 'Customers',
    href: '/customers',
    icon: Users,
  },
  {
    name: 'Billing',
    href: '/billing',
    icon: CreditCard,
  },
  {
    name: 'Sales',
    href: '/sales',
    icon: BarChart,
  },
  {
    name: 'Customer Journeys',
    href: '/journeys',
    icon: GitBranch,
    children: [
      {
        name: 'Lead Tracking',
        href: '/journeys/leads',
        icon: Activity,
      },
      {
        name: 'Conversion Analytics',
        href: '/journeys/conversion',
        icon: BarChart,
      },
    ],
  },
  {
    name: 'Support',
    href: '/support',
    icon: AlertTriangle,
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];

/**
 * Customer Portal Navigation
 */
export const customerNavigation: NavigationItem[] = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: Home,
  },
  {
    name: 'Services',
    href: '/services',
    icon: Server,
  },
  {
    name: 'Billing',
    href: '/billing',
    icon: CreditCard,
  },
  {
    name: 'Support',
    href: '/support',
    icon: AlertTriangle,
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];

/**
 * Technician Portal Navigation
 */
export const technicianNavigation: NavigationItem[] = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: Home,
  },
  {
    name: 'Work Orders',
    href: '/work-orders',
    icon: Settings,
  },
  {
    name: 'Network Tools',
    href: '/network',
    icon: Network,
    children: [
      {
        name: 'Diagnostics',
        href: '/network/diagnostics',
        icon: Activity,
      },
      {
        name: 'Device Status',
        href: '/network/devices',
        icon: Server,
      },
    ],
  },
  {
    name: 'Assets',
    href: '/assets',
    icon: Package,
    children: [
      {
        name: 'Field Inventory',
        href: '/assets/field',
        icon: Package,
      },
      {
        name: 'Maintenance Tasks',
        href: '/assets/maintenance',
        icon: Settings,
      },
    ],
  },
];

/**
 * Get navigation items for a specific portal
 */
export function getNavigationForPortal(portal: string): NavigationItem[] {
  switch (portal) {
    case 'management':
    case 'management-admin':
      return managementNavigation;
    case 'reseller':
    case 'management-reseller':
      return resellerNavigation;
    case 'customer':
      return customerNavigation;
    case 'technician':
      return technicianNavigation;
    default:
      return managementNavigation;
  }
}
