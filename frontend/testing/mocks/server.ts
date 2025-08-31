/**
 * DRY MSW (Mock Service Worker) setup for consistent API mocking.
 * Shared across all frontend applications.
 */

// Conditional import to handle Jest environment issues
let setupServer: any;
let http: any;
let HttpResponse: any;

try {
  // Import MSW v2 syntax
  const { setupServer: _setupServer } = require('msw/node');
  const { http: _http, HttpResponse: _HttpResponse } = require('msw');
  
  setupServer = _setupServer;
  http = _http;
  HttpResponse = _HttpResponse;
} catch (error) {
  // Fallback for test environments that can't load MSW
  console.warn('MSW could not be loaded, using mock fallback:', error.message);
  
  setupServer = () => ({
    listen: () => {},
    close: () => {},
    resetHandlers: () => {}
  });
  
  http = {
    get: () => {},
    post: () => {},
    put: () => {},
    delete: () => {},
    patch: () => {}
  };
  
  HttpResponse = {
    json: (data: any) => ({ json: () => Promise.resolve(data) }),
    text: (text: string) => ({ text: () => Promise.resolve(text) }),
    error: () => ({ error: true })
  };
}

// DRY API base configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

interface CrudOptions {
  basePath?: string;
  requireAuth?: boolean;
  delay?: number;
}

/**
 * DRY handler generator for CRUD operations
 */
const createCrudHandlers = (resource: string, factory: any, options: CrudOptions = {}): any[] => {
  const {
    basePath = `${API_BASE_URL}/${resource}`,
    requireAuth = true,
    delay = 0
  } = options;

  // In-memory data store for testing
  let dataStore: any[] = [];
  let nextId = 1;

  return [
    // GET /resource - List items
    http.get(basePath, async ({ request }) => {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));

      const url = new URL(request.url);
      const page = parseInt(url.searchParams.get('page') || '1');
      const limit = parseInt(url.searchParams.get('limit') || '10');
      const search = url.searchParams.get('search');

      let filteredData = dataStore;

      // Simple search filtering
      if (search) {
        filteredData = dataStore.filter(item =>
          JSON.stringify(item).toLowerCase().includes(search.toLowerCase())
        );
      }

      // Pagination
      const start = (page - 1) * limit;
      const end = start + limit;
      const paginatedData = filteredData.slice(start, end);

      return HttpResponse.json({
        data: paginatedData,
        meta: {
          page,
          limit,
          total: filteredData.length,
          totalPages: Math.ceil(filteredData.length / limit)
        }
      });
    }),

    // GET /resource/:id - Get single item
    http.get(`${basePath}/:id`, async ({ params }) => {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));

      const id = params.id;
      const item = dataStore.find(item => item.id == id);

      if (!item) {
        return HttpResponse.json(
          { error: 'Not found', message: `${resource} not found` },
          { status: 404 }
        );
      }

      return HttpResponse.json({ data: item });
    }),

    // POST /resource - Create item
    http.post(basePath, async ({ request }) => {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));

      const body = await request.json() as any;
      const newItem = factory({ ...body, id: nextId++ });
      dataStore.push(newItem);

      return HttpResponse.json({ data: newItem }, { status: 201 });
    }),

    // PUT /resource/:id - Update item
    http.put(`${basePath}/:id`, async ({ params, request }) => {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));

      const id = params.id;
      const body = await request.json() as any;
      const index = dataStore.findIndex(item => item.id == id);

      if (index === -1) {
        return HttpResponse.json(
          { error: 'Not found', message: `${resource} not found` },
          { status: 404 }
        );
      }

      dataStore[index] = { ...dataStore[index], ...body, updatedAt: new Date().toISOString() };

      return HttpResponse.json({ data: dataStore[index] });
    }),

    // DELETE /resource/:id - Delete item
    http.delete(`${basePath}/:id`, async ({ params }) => {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));

      const id = params.id;
      const index = dataStore.findIndex(item => item.id == id);

      if (index === -1) {
        return HttpResponse.json(
          { error: 'Not found', message: `${resource} not found` },
          { status: 404 }
        );
      }

      dataStore.splice(index, 1);

      return HttpResponse.json({ success: true }, { status: 204 });
    })
  ];
};

// Mock data factories
const mockCustomer = (overrides = {}) => ({
  id: `customer_${Math.random().toString(36).substr(2, 9)}`,
  name: 'Test Customer',
  email: 'customer@test.com',
  status: 'active',
  plan: 'Fiber 100Mbps',
  monthly_cost: 79.99,
  ...overrides
});

const mockWorkOrder = (overrides = {}) => ({
  id: `wo_${Math.random().toString(36).substr(2, 9)}`,
  customer_id: 'customer_123',
  type: 'installation',
  status: 'pending',
  priority: 'medium',
  scheduled_date: new Date().toISOString(),
  ...overrides
});

// Core API handlers
const coreHandlers = [
  // Customer portal APIs
  http.get('/api/v1/customer/dashboard', () => {
    return HttpResponse.json({
      account: {
        id: 'CUST-TEST-001',
        name: 'Test Customer',
        status: 'active',
        plan: 'Fiber 1000Mbps',
        monthly_cost: 89.99
      },
      service: {
        status: 'online',
        connection_speed: '1000 Mbps',
        uptime: 99.8
      }
    });
  }),

  http.get('/api/v1/customer/billing', () => {
    return HttpResponse.json({
      current_balance: 0.00,
      next_amount: 89.99,
      payment_method: {
        type: 'card',
        last_four: '4321'
      }
    });
  }),

  // Admin portal APIs  
  http.get('/api/v1/admin/customers', () => {
    return HttpResponse.json({
      customers: [mockCustomer()],
      total: 1
    });
  }),

  // Technician portal APIs
  http.get('/api/v1/technician/work-orders', () => {
    return HttpResponse.json({
      work_orders: [mockWorkOrder()],
      total: 1
    });
  }),

  // Auth APIs
  http.post('/api/auth/validate', () => {
    return HttpResponse.json({
      valid: true,
      user: { id: 'test-user', name: 'Test User' }
    });
  }),

  http.post('/api/auth/refresh', () => {
    return HttpResponse.json({
      token: 'new-test-token',
      expires_at: Date.now() + 24 * 60 * 60 * 1000
    });
  })
];

// Create and configure the mock server
export const server = setupServer(...coreHandlers);

// Helper functions
export const startServer = () => server.listen({ onUnhandledRequest: 'warn' });
export const stopServer = () => server.close();
export const resetServer = () => server.resetHandlers();