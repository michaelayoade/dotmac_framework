/**
 * Centralized route configuration for ISP platform
 */

export interface RouteDefinition {
  path: string;
  name: string;
  component?: string;
  layout?: string;
  requiredRoles?: string[];
  requiredPermissions?: string[];
  requiredFeatures?: string[];
  allowedPortals?: Array<'admin' | 'customer' | 'reseller'>;
  isPublic?: boolean;
  exact?: boolean;
  children?: RouteDefinition[];
  meta?: {
    title?: string;
    description?: string;
    breadcrumb?: string;
    icon?: string;
    badge?: string;
    hidden?: boolean;
    order?: number;
  };
}

// Admin Portal Routes
const ADMIN_ROUTES: RouteDefinition[] = [
  {
    path: '/admin',
    name: 'admin.dashboard',
    allowedPortals: ['admin'],
    meta: {
      title: 'Admin Dashboard',
      breadcrumb: 'Dashboard',
      icon: 'dashboard',
    },
  },
  {
    path: '/admin/customers',
    name: 'admin.customers',
    allowedPortals: ['admin'],
    requiredPermissions: ['customers:read'],
    meta: {
      title: 'Customer Management',
      breadcrumb: 'Customers',
      icon: 'users',
    },
    children: [
      {
        path: '/admin/customers/list',
        name: 'admin.customers.list',
        meta: {
          title: 'Customer List',
          breadcrumb: 'List',
        },
      },
      {
        path: '/admin/customers/create',
        name: 'admin.customers.create',
        requiredPermissions: ['customers:create'],
        meta: {
          title: 'Create Customer',
          breadcrumb: 'Create',
        },
      },
      {
        path: '/admin/customers/:id',
        name: 'admin.customers.detail',
        meta: {
          title: 'Customer Details',
          breadcrumb: 'Details',
        },
      },
      {
        path: '/admin/customers/:id/edit',
        name: 'admin.customers.edit',
        requiredPermissions: ['customers:update'],
        meta: {
          title: 'Edit Customer',
          breadcrumb: 'Edit',
        },
      },
    ],
  },
  {
    path: '/admin/network',
    name: 'admin.network',
    allowedPortals: ['admin'],
    requiredPermissions: ['network:read'],
    meta: {
      title: 'Network Management',
      breadcrumb: 'Network',
      icon: 'network',
    },
    children: [
      {
        path: '/admin/network/overview',
        name: 'admin.network.overview',
        meta: {
          title: 'Network Overview',
          breadcrumb: 'Overview',
        },
      },
      {
        path: '/admin/network/devices',
        name: 'admin.network.devices',
        requiredPermissions: ['devices:read'],
        meta: {
          title: 'Network Devices',
          breadcrumb: 'Devices',
        },
      },
      {
        path: '/admin/network/devices/:id',
        name: 'admin.network.devices.detail',
        meta: {
          title: 'Device Details',
          breadcrumb: 'Device',
        },
      },
      {
        path: '/admin/network/monitoring',
        name: 'admin.network.monitoring',
        requiredPermissions: ['monitoring:read'],
        meta: {
          title: 'Network Monitoring',
          breadcrumb: 'Monitoring',
        },
      },
      {
        path: '/admin/network/topology',
        name: 'admin.network.topology',
        requiredPermissions: ['topology:read'],
        meta: {
          title: 'Network Topology',
          breadcrumb: 'Topology',
        },
      },
    ],
  },
  {
    path: '/admin/billing',
    name: 'admin.billing',
    allowedPortals: ['admin'],
    requiredPermissions: ['billing:read'],
    meta: {
      title: 'Billing Management',
      breadcrumb: 'Billing',
      icon: 'billing',
    },
    children: [
      {
        path: '/admin/billing/overview',
        name: 'admin.billing.overview',
        meta: {
          title: 'Billing Overview',
          breadcrumb: 'Overview',
        },
      },
      {
        path: '/admin/billing/invoices',
        name: 'admin.billing.invoices',
        requiredPermissions: ['invoices:read'],
        meta: {
          title: 'Invoice Management',
          breadcrumb: 'Invoices',
        },
      },
      {
        path: '/admin/billing/payments',
        name: 'admin.billing.payments',
        requiredPermissions: ['payments:read'],
        meta: {
          title: 'Payment Processing',
          breadcrumb: 'Payments',
        },
      },
      {
        path: '/admin/billing/tariffs',
        name: 'admin.billing.tariffs',
        requiredPermissions: ['tariffs:read'],
        meta: {
          title: 'Tariff Management',
          breadcrumb: 'Tariffs',
        },
      },
    ],
  },
  {
    path: '/admin/support',
    name: 'admin.support',
    allowedPortals: ['admin'],
    requiredPermissions: ['support:read'],
    meta: {
      title: 'Support Management',
      breadcrumb: 'Support',
      icon: 'support',
    },
    children: [
      {
        path: '/admin/support/tickets',
        name: 'admin.support.tickets',
        meta: {
          title: 'Support Tickets',
          breadcrumb: 'Tickets',
        },
      },
      {
        path: '/admin/support/tickets/:id',
        name: 'admin.support.tickets.detail',
        meta: {
          title: 'Ticket Details',
          breadcrumb: 'Ticket',
        },
      },
      {
        path: '/admin/support/knowledge',
        name: 'admin.support.knowledge',
        meta: {
          title: 'Knowledge Base',
          breadcrumb: 'Knowledge Base',
        },
      },
    ],
  },
  {
    path: '/admin/analytics',
    name: 'admin.analytics',
    allowedPortals: ['admin'],
    requiredPermissions: ['analytics:read'],
    meta: {
      title: 'Analytics',
      breadcrumb: 'Analytics',
      icon: 'analytics',
    },
  },
  {
    path: '/admin/settings',
    name: 'admin.settings',
    allowedPortals: ['admin'],
    requiredPermissions: ['settings:read'],
    requiredRoles: ['tenant-admin', 'super-admin'],
    meta: {
      title: 'Settings',
      breadcrumb: 'Settings',
      icon: 'settings',
    },
  },
];

// Customer Portal Routes
const CUSTOMER_ROUTES: RouteDefinition[] = [
  {
    path: '/',
    name: 'customer.dashboard',
    allowedPortals: ['customer'],
    meta: {
      title: 'Customer Dashboard',
      breadcrumb: 'Dashboard',
      icon: 'dashboard',
    },
  },
  {
    path: '/services',
    name: 'customer.services',
    allowedPortals: ['customer'],
    requiredPermissions: ['services:read'],
    meta: {
      title: 'My Services',
      breadcrumb: 'Services',
      icon: 'services',
    },
  },
  {
    path: '/usage',
    name: 'customer.usage',
    allowedPortals: ['customer'],
    requiredPermissions: ['usage:read'],
    meta: {
      title: 'Usage Analytics',
      breadcrumb: 'Usage',
      icon: 'usage',
    },
  },
  {
    path: '/billing',
    name: 'customer.billing',
    allowedPortals: ['customer'],
    requiredPermissions: ['billing:read'],
    meta: {
      title: 'Billing & Payments',
      breadcrumb: 'Billing',
      icon: 'billing',
    },
    children: [
      {
        path: '/billing/invoices',
        name: 'customer.billing.invoices',
        meta: {
          title: 'My Invoices',
          breadcrumb: 'Invoices',
        },
      },
      {
        path: '/billing/payments',
        name: 'customer.billing.payments',
        meta: {
          title: 'Payment History',
          breadcrumb: 'Payments',
        },
      },
    ],
  },
  {
    path: '/support',
    name: 'customer.support',
    allowedPortals: ['customer'],
    meta: {
      title: 'Support Center',
      breadcrumb: 'Support',
      icon: 'support',
    },
    children: [
      {
        path: '/support/tickets',
        name: 'customer.support.tickets',
        meta: {
          title: 'My Tickets',
          breadcrumb: 'Tickets',
        },
      },
      {
        path: '/support/knowledge',
        name: 'customer.support.knowledge',
        meta: {
          title: 'Help Center',
          breadcrumb: 'Help',
        },
      },
    ],
  },
  {
    path: '/documents',
    name: 'customer.documents',
    allowedPortals: ['customer'],
    requiredPermissions: ['documents:read'],
    meta: {
      title: 'Documents',
      breadcrumb: 'Documents',
      icon: 'documents',
    },
  },
  {
    path: '/settings',
    name: 'customer.settings',
    allowedPortals: ['customer'],
    meta: {
      title: 'Account Settings',
      breadcrumb: 'Settings',
      icon: 'settings',
    },
  },
];

// Reseller Portal Routes
const RESELLER_ROUTES: RouteDefinition[] = [
  {
    path: '/',
    name: 'reseller.dashboard',
    allowedPortals: ['reseller'],
    meta: {
      title: 'Reseller Dashboard',
      breadcrumb: 'Dashboard',
      icon: 'dashboard',
    },
  },
  {
    path: '/customers',
    name: 'reseller.customers',
    allowedPortals: ['reseller'],
    requiredPermissions: ['customers:read'],
    meta: {
      title: 'Customer Management',
      breadcrumb: 'Customers',
      icon: 'customers',
    },
    children: [
      {
        path: '/customers/list',
        name: 'reseller.customers.list',
        meta: {
          title: 'Customer List',
          breadcrumb: 'List',
        },
      },
      {
        path: '/customers/onboard',
        name: 'reseller.customers.onboard',
        requiredPermissions: ['customers:create'],
        meta: {
          title: 'Onboard Customer',
          breadcrumb: 'Onboard',
        },
      },
    ],
  },
  {
    path: '/sales',
    name: 'reseller.sales',
    allowedPortals: ['reseller'],
    meta: {
      title: 'Sales Management',
      breadcrumb: 'Sales',
      icon: 'sales',
    },
  },
  {
    path: '/commissions',
    name: 'reseller.commissions',
    allowedPortals: ['reseller'],
    requiredPermissions: ['commissions:read'],
    meta: {
      title: 'Commission Tracking',
      breadcrumb: 'Commissions',
      icon: 'commissions',
    },
  },
  {
    path: '/territory',
    name: 'reseller.territory',
    allowedPortals: ['reseller'],
    requiredPermissions: ['territory:read'],
    requiredRoles: ['reseller-admin'],
    meta: {
      title: 'Territory Management',
      breadcrumb: 'Territory',
      icon: 'territory',
    },
  },
  {
    path: '/analytics',
    name: 'reseller.analytics',
    allowedPortals: ['reseller'],
    requiredPermissions: ['analytics:read'],
    requiredRoles: ['reseller-admin'],
    meta: {
      title: 'Sales Analytics',
      breadcrumb: 'Analytics',
      icon: 'analytics',
    },
  },
];

// Public Routes (available across all portals)
const PUBLIC_ROUTES: RouteDefinition[] = [
  {
    path: '/login',
    name: 'auth.login',
    isPublic: true,
    meta: {
      title: 'Sign In',
      hidden: true,
    },
  },
  {
    path: '/forgot-password',
    name: 'auth.forgot-password',
    isPublic: true,
    meta: {
      title: 'Forgot Password',
      hidden: true,
    },
  },
  {
    path: '/reset-password',
    name: 'auth.reset-password',
    isPublic: true,
    meta: {
      title: 'Reset Password',
      hidden: true,
    },
  },
  {
    path: '/unauthorized',
    name: 'error.unauthorized',
    isPublic: true,
    meta: {
      title: 'Unauthorized',
      hidden: true,
    },
  },
  {
    path: '/terms',
    name: 'legal.terms',
    isPublic: true,
    meta: {
      title: 'Terms of Service',
      hidden: true,
    },
  },
  {
    path: '/privacy',
    name: 'legal.privacy',
    isPublic: true,
    meta: {
      title: 'Privacy Policy',
      hidden: true,
    },
  },
];

// Combined route configuration
export const ROUTE_CONFIG: Record<string, RouteDefinition[]> = {
  admin: [...ADMIN_ROUTES, ...PUBLIC_ROUTES],
  customer: [...CUSTOMER_ROUTES, ...PUBLIC_ROUTES],
  reseller: [...RESELLER_ROUTES, ...PUBLIC_ROUTES],
  public: PUBLIC_ROUTES,
};

// Route utilities
export class RouteUtils {
  static findRouteByPath(routes: RouteDefinition[], path: string): RouteDefinition | null {
    for (const route of routes) {
      if (route.path === path) {
        return route;
      }
      if (route.children) {
        const childRoute = this.findRouteByPath(route.children, path);
        if (childRoute) {
          return childRoute;
        }
      }
    }
    return null;
  }

  static findRouteByName(routes: RouteDefinition[], name: string): RouteDefinition | null {
    for (const route of routes) {
      if (route.name === name) {
        return route;
      }
      if (route.children) {
        const childRoute = this.findRouteByName(route.children, name);
        if (childRoute) {
          return childRoute;
        }
      }
    }
    return null;
  }

  static getRouteBreadcrumbs(routes: RouteDefinition[], path: string): RouteDefinition[] {
    const breadcrumbs: RouteDefinition[] = [];
    
    const findBreadcrumbs = (routes: RouteDefinition[], targetPath: string, parents: RouteDefinition[] = []) => {
      for (const route of routes) {
        const currentPath = [...parents, route];
        
        if (route.path === targetPath) {
          breadcrumbs.push(...currentPath);
          return true;
        }
        
        if (route.children) {
          if (findBreadcrumbs(route.children, targetPath, currentPath)) {
            return true;
          }
        }
      }
      return false;
    };
    
    findBreadcrumbs(routes, path);
    return breadcrumbs;
  }

  static getMenuItems(routes: RouteDefinition[]): RouteDefinition[] {
    return routes.filter(route => !route.meta?.hidden && !route.isPublic);
  }

  static buildUrlPath(routeName: string, params: Record<string, string> = {}): string {
    // Find route by name across all portal routes
    for (const portalRoutes of Object.values(ROUTE_CONFIG)) {
      const route = this.findRouteByName(portalRoutes, routeName);
      if (route) {
        let path = route.path;
        // Replace parameters
        for (const [key, value] of Object.entries(params)) {
          path = path.replace(`:${key}`, value);
        }
        return path;
      }
    }
    return '/';
  }
}

// Default export for easy importing
export default ROUTE_CONFIG;