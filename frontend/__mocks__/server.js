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
