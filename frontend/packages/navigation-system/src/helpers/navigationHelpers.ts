import type { LucideIcon } from 'lucide-react';
import type { NavigationItem, NavigationVariant, BreadcrumbItem, NavigationUser, NavigationBranding } from '../types';

// Navigation Builder Helper
export class NavigationBuilder {
  private items: NavigationItem[] = [];

  static create(): NavigationBuilder {
    return new NavigationBuilder();
  }

  addItem(
    id: string,
    label: string,
    href: string,
    options?: {
      icon?: LucideIcon;
      badge?: string | number;
      description?: string;
      disabled?: boolean;
    }
  ): NavigationBuilder {
    this.items.push({
      id,
      label,
      href,
      ...options,
    });
    return this;
  }

  addGroup(
    id: string,
    label: string,
    children: NavigationItem[],
    options?: {
      icon?: LucideIcon;
      href?: string;
      description?: string;
      disabled?: boolean;
    }
  ): NavigationBuilder {
    this.items.push({
      id,
      label,
      href: options?.href || '#',
      children,
      ...options,
    });
    return this;
  }

  addSeparator(id?: string): NavigationBuilder {
    this.items.push({
      id: id || `separator-${Date.now()}`,
      label: '',
      href: '#',
      disabled: true,
    });
    return this;
  }

  build(): NavigationItem[] {
    return this.items;
  }
}

// Portal Navigation Presets
export const NavigationPresets = {
  admin: () => NavigationBuilder.create()
    .addItem('dashboard', 'Dashboard', '/dashboard', { icon: require('lucide-react').Home })
    .addItem('users', 'Users', '/users', { icon: require('lucide-react').Users })
    .addItem('analytics', 'Analytics', '/analytics', { icon: require('lucide-react').BarChart })
    .addItem('security', 'Security', '/security', { icon: require('lucide-react').Shield })
    .addItem('settings', 'Settings', '/settings', { icon: require('lucide-react').Settings })
    .build(),

  customer: () => NavigationBuilder.create()
    .addItem('dashboard', 'Dashboard', '/dashboard', { icon: require('lucide-react').Home })
    .addItem('account', 'My Account', '/account', { icon: require('lucide-react').User })
    .addItem('billing', 'Billing', '/billing', { icon: require('lucide-react').CreditCard })
    .addItem('services', 'Services', '/services', { icon: require('lucide-react').FileText })
    .addItem('support', 'Support', '/support', { icon: require('lucide-react').Headphones })
    .addItem('settings', 'Settings', '/settings', { icon: require('lucide-react').Settings })
    .build(),

  reseller: () => NavigationBuilder.create()
    .addItem('dashboard', 'Dashboard', '/dashboard', { icon: require('lucide-react').Home })
    .addItem('customers', 'Customers', '/customers', { icon: require('lucide-react').Users })
    .addItem('territories', 'Territories', '/territories', { icon: require('lucide-react').MapPin })
    .addItem('sales', 'Sales', '/sales', { icon: require('lucide-react').TrendingUp })
    .addItem('commissions', 'Commissions', '/commissions', { icon: require('lucide-react').CreditCard })
    .addItem('opportunities', 'Opportunities', '/opportunities', { icon: require('lucide-react').Briefcase })
    .addItem('support', 'Support', '/support', { icon: require('lucide-react').Headphones })
    .addItem('settings', 'Settings', '/settings', { icon: require('lucide-react').Settings })
    .build(),

  technician: () => NavigationBuilder.create()
    .addItem('dashboard', 'Dashboard', '/dashboard', { icon: require('lucide-react').Home })
    .addItem('work-orders', 'Work Orders', '/work-orders', { icon: require('lucide-react').Clipboard })
    .addItem('camera-demo', 'Camera & Scanner', '/camera-demo', { icon: require('lucide-react').Camera })
    .addItem('customers', 'Customers', '/customers', { icon: require('lucide-react').Users })
    .addItem('inventory', 'Inventory', '/inventory', { icon: require('lucide-react').Package })
    .addItem('schedule', 'Schedule', '/schedule', { icon: require('lucide-react').Calendar })
    .addItem('maps', 'Maps', '/maps', { icon: require('lucide-react').Map })
    .addItem('settings', 'Settings', '/settings', { icon: require('lucide-react').Settings })
    .build(),

  management: () => NavigationBuilder.create()
    .addItem('overview', 'Overview', '/overview', { icon: require('lucide-react').BarChart3 })
    .addItem('tenants', 'Tenants', '/tenants', { icon: require('lucide-react').Building })
    .addItem('users', 'Users', '/users', { icon: require('lucide-react').Users })
    .addItem('billing', 'Billing', '/billing', { icon: require('lucide-react').CreditCard })
    .addItem('security', 'Security', '/security', { icon: require('lucide-react').Shield })
    .addItem('system', 'System', '/system', { icon: require('lucide-react').Server })
    .addItem('settings', 'Settings', '/settings', { icon: require('lucide-react').Settings })
    .build(),
};

// Breadcrumb Builder Helper
export class BreadcrumbBuilder {
  private items: BreadcrumbItem[] = [];

  static create(): BreadcrumbBuilder {
    return new BreadcrumbBuilder();
  }

  static fromPath(path: string, labels?: Record<string, string>): BreadcrumbBuilder {
    const builder = new BreadcrumbBuilder();
    const segments = path.split('/').filter(Boolean);

    segments.forEach((segment, index) => {
      const isLast = index === segments.length - 1;
      const href = isLast ? undefined : ('/' + segments.slice(0, index + 1).join('/'));
      const label = labels?.[segment] || segment.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

      builder.addItem(segment, label, href, isLast);
    });

    return builder;
  }

  addItem(id: string, label: string, href?: string, current = false): BreadcrumbBuilder {
    this.items.push({ id, label, href, current });
    return this;
  }

  addHome(href = '/', label = 'Home'): BreadcrumbBuilder {
    this.items.unshift({ id: 'home', label, href });
    return this;
  }

  build(): BreadcrumbItem[] {
    return this.items;
  }
}

// User Helper
export const UserHelper = {
  format: (user: any): NavigationUser => ({
    id: user?.id || '',
    name: user?.name || user?.displayName || 'Unknown User',
    email: user?.email || '',
    avatar: user?.avatar || user?.picture,
    role: user?.role || user?.userType || 'User',
  }),

  getInitials: (user: NavigationUser): string => {
    return user.name
      .split(' ')
      .map(name => name.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  },

  getDisplayName: (user: NavigationUser): string => {
    return user.name || user.email.split('@')[0] || 'User';
  },
};

// Branding Helper
export const BrandingHelper = {
  fromTenant: (tenant: any): NavigationBranding => ({
    logo: tenant?.branding?.logo,
    logoUrl: tenant?.branding?.logoUrl,
    companyName: tenant?.name || tenant?.companyName || 'Portal',
    primaryColor: tenant?.branding?.primaryColor || '#3B82F6',
    secondaryColor: tenant?.branding?.secondaryColor || '#1E40AF',
  }),

  getVariantColors: (variant: NavigationVariant) => {
    const colors = {
      admin: { primary: '#3B82F6', secondary: '#1E40AF' },
      customer: { primary: '#22C55E', secondary: '#15803D' },
      reseller: { primary: '#9333EA', secondary: '#7C3AED' },
      technician: { primary: '#F59E0B', secondary: '#D97706' },
      management: { primary: '#6B7280', secondary: '#4B5563' },
    };
    return colors[variant];
  },
};

// Route Helper
export const RouteHelper = {
  extractActiveItem: (path: string, items: NavigationItem[]): string | undefined => {
    // Find exact match first
    const exactMatch = items.find(item => item.href === path);
    if (exactMatch) return exactMatch.id;

    // Find best partial match
    const matches = items
      .filter(item => path.startsWith(item.href) && item.href !== '/')
      .sort((a, b) => b.href.length - a.href.length);

    return matches[0]?.id;
  },

  generatePaths: (items: NavigationItem[], basePath = ''): Record<string, string> => {
    const paths: Record<string, string> = {};

    items.forEach(item => {
      paths[item.id] = basePath + item.href;

      if (item.children) {
        const childPaths = RouteHelper.generatePaths(item.children, basePath);
        Object.assign(paths, childPaths);
      }
    });

    return paths;
  },

  isActive: (itemHref: string, currentPath: string): boolean => {
    if (itemHref === currentPath) return true;
    if (itemHref === '/' && currentPath === '/') return true;
    if (itemHref !== '/' && currentPath.startsWith(itemHref)) return true;
    return false;
  },
};

// Badge Helper
export const BadgeHelper = {
  format: (value: string | number | undefined): string | undefined => {
    if (value === undefined || value === null) return undefined;

    if (typeof value === 'number') {
      return value > 99 ? '99+' : value.toString();
    }

    return value.toString();
  },

  getVariant: (value: string | number | undefined, type: 'info' | 'warning' | 'error' | 'success' = 'info') => {
    if (!value) return undefined;

    const variants = {
      info: 'bg-blue-100 text-blue-800',
      warning: 'bg-yellow-100 text-yellow-800',
      error: 'bg-red-100 text-red-800',
      success: 'bg-green-100 text-green-800',
    };

    return {
      value: BadgeHelper.format(value),
      className: variants[type],
    };
  },
};

// Navigation Hook Helpers
export const NavigationHookHelpers = {
  createNavigationHandler: (router: any) => (item: NavigationItem) => {
    if (router?.push) {
      router.push(item.href);
    } else if (router?.navigate) {
      router.navigate(item.href);
    } else {
      window.location.href = item.href;
    }
  },

  createLogoutHandler: (authService: any, redirectPath = '/login') => async () => {
    try {
      if (authService?.logout) {
        await authService.logout();
      }
      window.location.href = redirectPath;
    } catch (error) {
      console.error('Logout failed:', error);
      window.location.href = redirectPath;
    }
  },

  createBreadcrumbHandler: (router: any) => (item: BreadcrumbItem) => {
    if (!item.href) return;

    if (router?.push) {
      router.push(item.href);
    } else if (router?.navigate) {
      router.navigate(item.href);
    } else {
      window.location.href = item.href;
    }
  },
};

// Migration Helper
export const MigrationHelper = {
  convertLegacyNavigation: (legacyItems: any[]): NavigationItem[] => {
    return legacyItems.map(item => ({
      id: item.key || item.id || item.name?.toLowerCase().replace(/\s+/g, '-'),
      label: item.title || item.label || item.name,
      href: item.path || item.href || item.url || '#',
      icon: item.icon,
      badge: item.badge || item.count,
      description: item.description || item.tooltip,
      disabled: item.disabled || item.hidden,
      children: (item.children || item.submenu) ?
        MigrationHelper.convertLegacyNavigation(item.children || item.submenu) : undefined,
    }));
  },

  validateNavigation: (items: NavigationItem[]): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];
    const ids = new Set<string>();

    const validateItem = (item: NavigationItem, depth = 0) => {
      // Check for duplicate IDs
      if (ids.has(item.id)) {
        errors.push(`Duplicate navigation ID: ${item.id}`);
      } else {
        ids.add(item.id);
      }

      // Check required fields
      if (!item.id) errors.push('Navigation item missing required ID');
      if (!item.label) errors.push(`Navigation item ${item.id} missing label`);
      if (!item.href) errors.push(`Navigation item ${item.id} missing href`);

      // Check depth
      if (depth > 3) {
        errors.push(`Navigation item ${item.id} exceeds maximum nesting depth (3)`);
      }

      // Validate children
      if (item.children) {
        item.children.forEach(child => validateItem(child, depth + 1));
      }
    };

    items.forEach(validateItem);

    return {
      valid: errors.length === 0,
      errors,
    };
  },
};
