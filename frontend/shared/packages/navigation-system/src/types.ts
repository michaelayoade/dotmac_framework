import type { LucideIcon } from 'lucide-react';
import type { ComponentProps, ReactNode } from 'react';

export interface NavigationItem {
  id: string;
  label: string;
  href: string;
  icon?: LucideIcon;
  badge?: string | number;
  description?: string;
  disabled?: boolean;
  children?: NavigationItem[];
}

export interface BreadcrumbItem {
  id: string;
  label: string;
  href?: string | undefined;
  current?: boolean;
}

export interface NavigationUser {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role?: string;
}

export interface NavigationBranding {
  logo?: ReactNode;
  logoUrl?: string;
  companyName: string;
  primaryColor?: string;
  secondaryColor?: string;
}

export interface NavigationTenant {
  id: string;
  name: string;
  subdomain?: string;
}

export type NavigationVariant = 'admin' | 'customer' | 'reseller' | 'technician' | 'management';
export type LayoutType = 'sidebar' | 'topbar' | 'hybrid';
export type SidebarBehavior = 'push' | 'overlay' | 'squeeze';
export type MobileNavigationVariant = 'drawer' | 'tabs' | 'bottom-sheet';

export interface NavigationContextValue {
  activeItem?: string | undefined;
  onNavigate?: (item: NavigationItem) => void;
  collapsed?: boolean;
  variant?: NavigationVariant;
  layoutType?: LayoutType;
}

export interface UniversalNavigationProps {
  items: NavigationItem[];
  activeItem?: string | undefined;
  variant?: NavigationVariant;
  layoutType?: LayoutType;
  user?: NavigationUser | undefined;
  branding?: NavigationBranding | undefined;
  tenant?: NavigationTenant | undefined;
  onNavigate?: (item: NavigationItem) => void;
  onLogout?: (() => void) | undefined;
  className?: string;
  children?: ReactNode;
}

export interface UniversalSidebarProps {
  items: NavigationItem[];
  activeItem?: string | undefined;
  variant?: NavigationVariant;
  collapsed?: boolean;
  collapsible?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
  behavior?: SidebarBehavior;
  width?: 'sm' | 'md' | 'lg' | 'xl';
  header?: ReactNode;
  footer?: ReactNode;
  onNavigate?: (item: NavigationItem) => void;
  className?: string;
}

export interface UniversalTopbarProps {
  items?: NavigationItem[];
  activeItem?: string | undefined;
  variant?: NavigationVariant;
  user?: NavigationUser | undefined;
  branding?: NavigationBranding | undefined;
  tenant?: NavigationTenant | undefined;
  actions?: ReactNode;
  onNavigate?: (item: NavigationItem) => void;
  onLogout?: (() => void) | undefined;
  className?: string;
}

export interface UniversalMobileNavigationProps {
  items: NavigationItem[];
  activeItem?: string | undefined;
  variant?: MobileNavigationVariant;
  onNavigate?: (item: NavigationItem) => void;
  className?: string;
}

export interface UniversalBreadcrumbProps extends ComponentProps<'nav'> {
  items: BreadcrumbItem[];
  separator?: ReactNode;
  maxItems?: number;
  showHome?: boolean;
  onNavigate?: (item: BreadcrumbItem) => void;
}

export interface UniversalTabNavigationProps {
  items: NavigationItem[];
  activeItem?: string | undefined;
  variant?: 'default' | 'pills' | 'underline' | 'cards';
  size?: 'sm' | 'md' | 'lg';
  orientation?: 'horizontal' | 'vertical';
  onNavigate?: (item: NavigationItem) => void;
  className?: string;
}
