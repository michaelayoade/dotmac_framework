import { 
  LayoutDashboard, 
  Users, 
  MapPin, 
  DollarSign, 
  BarChart3, 
  GraduationCap,
  Settings,
  Shield,
  Target,
  FileText,
  Award,
} from 'lucide-react';
import type { ComponentType } from 'react';
import { Permission } from '@/lib/permissions/PermissionSystem';

export interface NavigationItem {
  name: string;
  href: string;
  icon: ComponentType<{ className?: string | undefined }>;
  badge?: string;
  permission?: string;
  children?: NavigationItem[];
}

export const navigationConfig: NavigationItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { 
    name: 'Partners', 
    href: '/partners', 
    icon: Users,
    permission: Permission.MANAGE_RESELLERS,
    children: [
      { name: 'All Partners', href: '/partners', icon: Users, permission: Permission.VIEW_PARTNERS },
      { name: 'Onboarding', href: '/partners/onboarding', icon: Target, permission: Permission.MANAGE_ONBOARDING },
      { name: 'Applications', href: '/partners/applications', icon: FileText, badge: '3', permission: Permission.PROCESS_APPLICATIONS },
    ]
  },
  { 
    name: 'Territories', 
    href: '/territories', 
    icon: MapPin,
    permission: Permission.MANAGE_TERRITORIES,
  },
  { 
    name: 'Commissions', 
    href: '/commissions', 
    icon: DollarSign,
    permission: Permission.VIEW_COMMISSIONS,
    children: [
      { name: 'Payments', href: '/commissions', icon: DollarSign, permission: Permission.APPROVE_COMMISSIONS },
      { name: 'Calculations', href: '/commissions/calculations', icon: BarChart3, permission: Permission.VIEW_COMMISSIONS },
      { name: 'Disputes', href: '/commissions/disputes', icon: Shield, badge: '2', permission: Permission.MANAGE_COMMISSION_DISPUTES },
    ]
  },
  { 
    name: 'Training', 
    href: '/training', 
    icon: GraduationCap,
    permission: Permission.MANAGE_TRAINING,
  },
  { 
    name: 'Analytics', 
    href: '/analytics', 
    icon: BarChart3,
    permission: Permission.VIEW_ANALYTICS,
  },
  { 
    name: 'Incentives', 
    href: '/incentives', 
    icon: Award,
    permission: Permission.VIEW_PARTNERS, // Assuming incentives are partner-related
  },
  { name: 'Settings', href: '/settings', icon: Settings },
];

// Navigation utility functions
export function findCurrentNavigation(navItems: NavigationItem[], path: string): NavigationItem | null {
  for (const item of navItems) {
    if (item.href === path) return item;
    if (item.children) {
      const found = findCurrentNavigation(item.children, path);
      if (found) return found;
    }
  }
  return null;
}

export function getCurrentPageTitle(filteredNavigation: NavigationItem[], pathname: string): string {
  const currentNav = findCurrentNavigation(filteredNavigation, pathname || '/');
  return currentNav?.name || 'Reseller Management';
}