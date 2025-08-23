/* eslint-disable @typescript-eslint/no-unused-vars */
/* biome-ignore lint/suspicious/noEmptyBlockStatements: Mock implementation */
/* biome-ignore lint/suspicious/noConsole: Development utility */
/* biome-ignore lint/correctness/noUnusedVariables: Mock fallback */
/* biome-ignore lint/style/useSingleVarDeclarator: Legacy format */
/* biome-ignore lint/style/useNamingConvention: API contract format */

/**
 * Mock Service Worker for API mocking
 * Follows backend testing patterns for comprehensive API mocking
 */

let setupServer;
let http;
let HttpResponse;

try {
  const mswNode = require('msw/node');
  const msw = require('msw');
  setupServer = mswNode.setupServer;
  http = msw.http;
  HttpResponse = msw.HttpResponse;
} catch (_error) {
  setupServer = () => ({ listen: () => {}, close: () => {}, resetHandlers: () => {} });
  http = { get: () => {}, post: () => {} };
  HttpResponse = { json: (data) => data };
}

// Mock API endpoints
const handlers = [
  // Authentication endpoints
  http.post('/api/v1/auth/login', () => {
    return HttpResponse.json({
      access_token: 'mock-jwt-token',
      token_type: 'bearer',
      user: {
        id: 'user-123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'customer',
        tenant: 'tenant-123',
      },
    });
  }),

  http.post('/api/v1/auth/logout', () => {
    return HttpResponse.json({ message: 'Logged out successfully' });
  }),

  http.get('/api/v1/auth/me', () => {
    return HttpResponse.json({
      id: 'user-123',
      email: 'test@example.com',
      name: 'Test User',
      role: 'customer',
      tenant: 'tenant-123',
    });
  }),

  // Customer endpoints
  http.get('/api/v1/customers', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'cust-1',
          name: 'Test Customer',
          email: 'customer@test.com',
          plan: 'enterprise',
          status: 'active',
          mrr: 299.99,
        },
      ],
      meta: { total: 1, page: 1, per_page: 10 },
    });
  }),

  http.get('/api/v1/customers/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'Test Customer',
      email: 'customer@test.com',
      plan: 'enterprise',
      status: 'active',
      mrr: 299.99,
      usage: {
        current: 1500,
        limit: 2000,
        percentage: 75,
      },
      billing: {
        balance: 0,
        next_bill: '2024-04-01',
        last_payment: '2024-03-01',
      },
    });
  }),

  // Services endpoints
  http.get('/api/v1/services', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'service-1',
          name: 'Internet Service',
          type: 'internet',
          status: 'active',
          speed: '100/20',
          monthly_price: 79.99,
        },
      ],
    });
  }),

  // Billing endpoints
  http.get('/api/v1/billing/invoices', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'inv-1',
          number: 'INV-2024-001',
          amount: 79.99,
          status: 'paid',
          due_date: '2024-03-01',
          created_at: '2024-02-01',
        },
      ],
    });
  }),

  // Analytics endpoints
  http.get('/api/v1/analytics/usage', () => {
    return HttpResponse.json({
      period: '30d',
      data: [
        { date: '2024-03-01', download: 50.5, upload: 12.3 },
        { date: '2024-03-02', download: 48.2, upload: 11.8 },
      ],
    });
  }),

  // Configuration endpoint
  http.get('/api/v1/config', () => {
    return HttpResponse.json({
      locale: {
        primary: 'en-US',
        supported: ['en-US'],
        fallback: 'en-US',
      },
      currency: {
        primary: 'USD',
        symbol: '$',
        position: 'before',
      },
      branding: {
        company: {
          name: 'Test ISP',
          colors: {
            primary: '#3b82f6',
            secondary: '#64748b',
          },
        },
      },
    });
  }),

  // Error scenarios for testing
  http.get('/api/v1/error/500', () => {
    return HttpResponse.json({ message: 'Internal Server Error' }, { status: 500 });
  }),

  http.get('/api/v1/error/404', () => {
    return HttpResponse.json({ message: 'Not Found' }, { status: 404 });
  }),

  http.get('/api/v1/error/unauthorized', () => {
    return HttpResponse.json({ message: 'Unauthorized' }, { status: 401 });
  }),

  // Licensing endpoints
  http.get('/api/licensing/licenses', ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '10');
    return HttpResponse.json({
      data: Array.from({ length: Math.min(limit, 50) }, (_, i) => ({
        id: `license-${i + 1}`,
        key: `LIC-${String(i + 1).padStart(4, '0')}`,
        customer_id: `cust-${i + 1}`,
        status: 'active',
        type: 'enterprise',
        expires_at: '2025-12-31T23:59:59Z',
        features: ['api_access', 'premium_support'],
        usage: { current: 150, limit: 1000 }
      })),
      meta: { total: 50, page: 1, per_page: limit }
    });
  }),

  http.post('/api/licensing/licenses', () => {
    return HttpResponse.json({
      id: 'license-new',
      key: 'LIC-NEW-001',
      status: 'active',
      message: 'License created successfully'
    }, { status: 201 });
  }),

  http.get('/api/licensing/licenses/:key', ({ params }) => {
    return HttpResponse.json({
      id: `license-${params.key}`,
      key: params.key,
      customer_id: 'cust-123',
      status: 'active',
      type: 'enterprise',
      expires_at: '2025-12-31T23:59:59Z',
      features: ['api_access', 'premium_support'],
      usage: { current: 150, limit: 1000 }
    });
  }),

  // Support endpoints
  http.get('/api/support/tickets', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'ticket-1',
          title: 'Connection Issue',
          status: 'open',
          priority: 'high',
          customer_id: 'cust-123',
          created_at: '2024-03-15T10:00:00Z',
          updated_at: '2024-03-15T14:30:00Z'
        }
      ],
      meta: { total: 1, page: 1, per_page: 10 }
    });
  }),

  // Services endpoints (extended)
  http.get('/api/services/services', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'service-1',
          name: 'Internet Service Pro',
          type: 'internet',
          status: 'active',
          speed_down: 100,
          speed_up: 20,
          monthly_price: 79.99,
          customer_id: 'cust-123'
        }
      ]
    });
  }),

  // Networking endpoints  
  http.get('/api/networking/devices', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'device-1',
          name: 'Router-001',
          type: 'router',
          status: 'online',
          ip_address: '192.168.1.1',
          mac_address: '00:11:22:33:44:55',
          last_seen: '2024-03-15T15:00:00Z'
        }
      ]
    });
  }),

  // Analytics endpoints (extended)
  http.get('/api/analytics/reports', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'report-1',
          name: 'Monthly Usage Report',
          type: 'usage',
          period: '30d',
          generated_at: '2024-03-15T12:00:00Z'
        }
      ]
    });
  }),

  // Identity endpoints
  http.get('/api/identity/customers', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'cust-1',
          name: 'John Doe', 
          email: 'john@example.com',
          portal_id: 'PORT123',
          status: 'active',
          created_at: '2024-01-15T10:00:00Z'
        }
      ],
      meta: { total: 1, page: 1, per_page: 10 }
    });
  }),

  http.post('/api/identity/customers', () => {
    return HttpResponse.json({
      id: 'cust-new',
      name: 'New Customer',
      email: 'new@example.com',
      portal_id: 'PORT456',
      status: 'active'
    }, { status: 201 });
  }),

  // Notifications endpoints
  http.get('/api/notifications/notifications', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'notif-1',
          title: 'Service Update',
          message: 'Your service has been updated',
          type: 'info',
          read: false,
          created_at: '2024-03-15T09:00:00Z'
        }
      ]
    });
  }),

  // Resellers endpoints
  http.get('/api/resellers/resellers', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'reseller-1',
          name: 'TechCorp Reseller',
          email: 'contact@techcorp.com',
          status: 'active',
          commission_rate: 0.15,
          customers_count: 25
        }
      ]
    });
  }),

  // Slow endpoint for testing loading states
  http.get('/api/v1/slow', async () => {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    return HttpResponse.json({ message: 'Slow response' });
  }),
];

// Create server instance
const server = setupServer(...handlers);

// Export handlers for individual test customization
module.exports = { server, handlers };
