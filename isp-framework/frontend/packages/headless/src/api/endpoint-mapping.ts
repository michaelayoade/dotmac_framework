/**
 * API Endpoint Mapping
 * Maps frontend expectations to actual backend API structure
 */

// Backend API structure from routers.py analysis:
export const BACKEND_ENDPOINTS = {
  // Identity & Authentication
  identity: '/api/v1/identity',
  auth: '/api/v1/identity/auth', // Assumed based on security middleware

  // Core Business Modules
  customers: '/api/v1/identity', // Customers are part of identity module
  billing: '/api/v1/billing',
  services: '/api/v1/services',
  support: '/api/v1/support',
  
  // Network Operations
  networking: '/api/v1/networking',
  networkMonitoring: '/api/v1/network-monitoring',
  networkVisualization: '/api/v1/network-visualization',
  
  // Other Modules
  analytics: '/api/v1/analytics',
  sales: '/api/v1/sales',
  inventory: '/api/v1/inventory',
  compliance: '/api/v1/compliance',
  fieldOps: '/api/v1/field-ops',
  licensing: '/api/v1/licensing',
  notifications: '/api/v1/notifications',
  portalManagement: '/api/v1/portal-management',
  resellers: '/api/v1/resellers',
  gis: '/api/v1/gis',
  
  // Portals
  admin: '/api/v1/admin',
  customer: '/api/v1/customer',
  reseller: '/api/v1/reseller',
  technician: '/api/v1/technician',
  
  // Security
  security: '/api/v1/security',
} as const;

// Frontend to Backend API mapping
export const API_MAPPING = {
  // Authentication endpoints
  'POST /api/v1/auth/login': 'POST /api/v1/identity/auth/login',
  'POST /api/v1/auth/logout': 'POST /api/v1/identity/auth/logout', 
  'POST /api/v1/auth/refresh': 'POST /api/v1/identity/auth/refresh',
  'GET /api/v1/auth/user': 'GET /api/v1/identity/auth/user',

  // Customer management (part of identity module)
  'GET /api/v1/customers': 'GET /api/v1/identity/customers',
  'POST /api/v1/customers': 'POST /api/v1/identity/customers',
  'GET /api/v1/customers/:id': 'GET /api/v1/identity/customers/:id',
  'PUT /api/v1/customers/:id': 'PUT /api/v1/identity/customers/:id',
  'DELETE /api/v1/customers/:id': 'DELETE /api/v1/identity/customers/:id',
  'POST /api/v1/customers/search': 'POST /api/v1/identity/customers/search',
  'POST /api/v1/customers/:id/services': 'POST /api/v1/identity/customers/:id/services',
  'POST /api/v1/customers/:id/suspend': 'POST /api/v1/identity/customers/:id/suspend',
  'POST /api/v1/customers/:id/restore': 'POST /api/v1/identity/customers/:id/restore',
  'GET /api/v1/customers/:id/analytics': 'GET /api/v1/analytics/customers/:id',

  // Billing operations
  'GET /api/v1/billing/invoices': 'GET /api/v1/billing/invoices',
  'POST /api/v1/billing/invoices': 'POST /api/v1/billing/invoices',
  'POST /api/v1/billing/usage/process': 'POST /api/v1/billing/usage/process',
  'POST /api/v1/billing/invoices/:id/payments': 'POST /api/v1/billing/invoices/:id/payments',
  'POST /api/v1/billing/invoices/:id/send': 'POST /api/v1/billing/invoices/:id/send',
  'POST /api/v1/billing/invoices/:id/remind': 'POST /api/v1/billing/invoices/:id/remind',
  'POST /api/v1/billing/payment-plans': 'POST /api/v1/billing/payment-plans',
  'GET /api/v1/billing/usage': 'GET /api/v1/billing/usage',
  'GET /api/v1/billing/tax-config': 'GET /api/v1/billing/tax-config',
  'POST /api/v1/billing/tax/calculate': 'POST /api/v1/billing/tax/calculate',
  'GET /api/v1/billing/analytics': 'GET /api/v1/analytics/billing',

  // Network operations
  'GET /api/v1/network/devices': 'GET /api/v1/networking/devices',
  'POST /api/v1/network/devices': 'POST /api/v1/networking/devices',
  'PUT /api/v1/network/devices/:id': 'PUT /api/v1/networking/devices/:id',
  'POST /api/v1/network/discovery': 'POST /api/v1/networking/discovery',
  'POST /api/v1/network/devices/:id/execute': 'POST /api/v1/networking/devices/:id/execute',
  'GET /api/v1/network/topology': 'GET /api/v1/network-visualization/topology',
  'POST /api/v1/network/topology/generate': 'POST /api/v1/network-visualization/topology/generate',
  'GET /api/v1/network/incidents': 'GET /api/v1/network-monitoring/incidents',
  'POST /api/v1/network/incidents': 'POST /api/v1/network-monitoring/incidents',
  'PUT /api/v1/network/incidents/:id/status': 'PUT /api/v1/network-monitoring/incidents/:id/status',
  'GET /api/v1/network/config-templates': 'GET /api/v1/networking/config-templates',
  'POST /api/v1/network/devices/:id/apply-config': 'POST /api/v1/networking/devices/:id/apply-config',
  'GET /api/v1/network/devices/:id/metrics': 'GET /api/v1/network-monitoring/devices/:id/metrics',

  // Service operations
  'POST /api/v1/services/provision': 'POST /api/v1/services/provision',
  'GET /api/v1/services/provision/:id/status': 'GET /api/v1/services/provision/:id/status',
  'POST /api/v1/services/customers/:id/suspend': 'POST /api/v1/services/customers/:id/suspend',
  'POST /api/v1/services/customers/:id/restore': 'POST /api/v1/services/customers/:id/restore',

  // Support operations
  'GET /api/v1/support/tickets': 'GET /api/v1/support/tickets',
  'POST /api/v1/support/tickets': 'POST /api/v1/support/tickets',
  'PUT /api/v1/support/tickets/:id/status': 'PUT /api/v1/support/tickets/:id/status',

  // Payment processing (these will need custom implementation)
  'POST /api/v1/payments/stripe/intents': 'POST /api/v1/billing/stripe/intents',
  'POST /api/v1/payments/stripe/setup-intents': 'POST /api/v1/billing/stripe/setup-intents', 
  'GET /api/v1/payments/stripe/customers/:id/payment-methods': 'GET /api/v1/billing/stripe/customers/:id/payment-methods',
  'POST /api/v1/payments/stripe/payment-methods/:id/detach': 'POST /api/v1/billing/stripe/payment-methods/:id/detach',
  'POST /api/v1/payments/stripe/refunds': 'POST /api/v1/billing/stripe/refunds',
  'POST /api/v1/payments/stripe/subscriptions': 'POST /api/v1/billing/stripe/subscriptions',
  
  'POST /api/v1/payments/paypal/orders': 'POST /api/v1/billing/paypal/orders',
  'POST /api/v1/payments/paypal/orders/:id/capture': 'POST /api/v1/billing/paypal/orders/:id/capture',
  'POST /api/v1/payments/paypal/subscriptions': 'POST /api/v1/billing/paypal/subscriptions',
} as const;

// Helper function to get the correct backend endpoint
export function getBackendEndpoint(frontendEndpoint: string): string {
  // Remove query parameters and normalize
  const normalized = frontendEndpoint.split('?')[0];
  
  // Check for exact match first
  const exactMatch = API_MAPPING[normalized as keyof typeof API_MAPPING];
  if (exactMatch) {
    return exactMatch;
  }

  // Check for pattern matches (with :id parameters)
  for (const [pattern, backendEndpoint] of Object.entries(API_MAPPING)) {
    const regex = new RegExp('^' + pattern.replace(/:[^/]+/g, '[^/]+') + '$');
    if (regex.test(normalized)) {
      // Replace :id patterns in backend endpoint with actual values
      let result = backendEndpoint;
      const frontendParts = normalized.split('/');
      const patternParts = pattern.split('/');
      
      patternParts.forEach((part, index) => {
        if (part.startsWith(':')) {
          result = result.replace(part, frontendParts[index]);
        }
      });
      
      return result;
    }
  }

  // Fallback: return original endpoint (will likely fail)
  console.warn(`No backend mapping found for: ${frontendEndpoint}`);
  return normalized;
}

// Type-safe endpoint builder
export function buildEndpoint(template: string, params: Record<string, string>): string {
  return template.replace(/:(\w+)/g, (match, key) => {
    if (!(key in params)) {
      throw new Error(`Missing parameter: ${key}`);
    }
    return params[key];
  });
}

export type BackendEndpoint = typeof BACKEND_ENDPOINTS[keyof typeof BACKEND_ENDPOINTS];
export type FrontendToBackendMapping = typeof API_MAPPING;