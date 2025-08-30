/**
 * DRY MSW (Mock Service Worker) setup for consistent API mocking.
 * Shared across all frontend applications.
 */

// Updated for MSW v2 - correct import paths
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { factories, createMockData } from '../factories';

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

      return HttpResponse.json(
        factories.ApiResponse.paginated(filteredData, page, limit)
      );
    }),

    // GET /resource/:id - Get single item
    http.get(`${basePath}/:id`, async ({ params }) => {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));

      const item = dataStore.find(item => item.id === params.id);

      if (!item) {
        return HttpResponse.json(
          factories.ApiResponse.error('Item not found', 404),
          { status: 404 }
        );
      }

      return HttpResponse.json(
        factories.ApiResponse.success(item)
      );
    }),

    // POST /resource - Create item
    http.post(basePath, async ({ request }) => {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));

      const body = await request.json();
      const newItem = factory.build({
        ...body,
        id: `${resource}-${nextId++}`,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      });

      dataStore.push(newItem);

      return HttpResponse.json(
        factories.ApiResponse.success(newItem),
        { status: 201 }
      );
    }),

    // PUT /resource/:id - Update item
    http.put(`${basePath}/:id`, async ({ params, request }) => {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));

      const itemIndex = dataStore.findIndex(item => item.id === params.id);

      if (itemIndex === -1) {
        return HttpResponse.json(
          factories.ApiResponse.error('Item not found', 404),
          { status: 404 }
        );
      }

      const body = await request.json();
      const updatedItem = {
        ...dataStore[itemIndex],
        ...body,
        updatedAt: new Date().toISOString()
      };

      dataStore[itemIndex] = updatedItem;

      return HttpResponse.json(
        factories.ApiResponse.success(updatedItem)
      );
    }),

    // DELETE /resource/:id - Delete item
    http.delete(`${basePath}/:id`, async ({ params }) => {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));

      const itemIndex = dataStore.findIndex(item => item.id === params.id);

      if (itemIndex === -1) {
        return HttpResponse.json(
          factories.ApiResponse.error('Item not found', 404),
          { status: 404 }
        );
      }

      dataStore.splice(itemIndex, 1);

      return HttpResponse.json(
        factories.ApiResponse.success({ deleted: true })
      );
    })
  ];
};

/**
 * DRY handlers for all main resources
 */
const handlers = [
  // Authentication handlers
  http.post(`${API_BASE_URL}/auth/login`, async ({ request }) => {
    const { email, password } = await request.json();

    // Simulate authentication logic
    if (email === 'admin@dotmac.io' && password === 'admin123') {
      return HttpResponse.json(
        factories.ApiResponse.success({
          user: createMockData.admin({ email }),
          token: 'mock-jwt-token',
          expiresIn: 3600
        })
      );
    }

    return HttpResponse.json(
      factories.ApiResponse.error('Invalid credentials', 401),
      { status: 401 }
    );
  }),

  http.post(`${API_BASE_URL}/auth/refresh`, async () => {
    return HttpResponse.json(
      factories.ApiResponse.success({
        token: 'new-mock-jwt-token',
        expiresIn: 3600
      })
    );
  }),

  http.post(`${API_BASE_URL}/auth/logout`, async () => {
    return HttpResponse.json(
      factories.ApiResponse.success({ message: 'Logged out successfully' })
    );
  }),

  // System info handlers
  http.get(`${API_BASE_URL}/system/info`, async () => {
    return HttpResponse.json(
      factories.ApiResponse.success({
        name: 'DotMac ISP Framework',
        version: '1.0.0',
        status: 'operational',
        uptime: '2 days, 4 hours'
      })
    );
  }),

  http.get(`${API_BASE_URL}/system/health`, async () => {
    return HttpResponse.json(
      factories.ApiResponse.success({
        status: 'healthy',
        checks: {
          database: 'connected',
          cache: 'operational',
          external_apis: 'accessible'
        }
      })
    );
  }),

  // Analytics handlers
  http.get(`${API_BASE_URL}/analytics/dashboard`, async () => {
    return HttpResponse.json(
      factories.ApiResponse.success(
        factories.Analytics.dashboard()
      )
    );
  }),

  // Performance monitoring
  http.get(`${API_BASE_URL}/performance/metrics`, async () => {
    return HttpResponse.json(
      factories.ApiResponse.success({
        metrics: [
          { name: 'response_time', value: 145, unit: 'ms' },
          { name: 'requests_per_second', value: 12.5, unit: 'req/s' },
          { name: 'error_rate', value: 0.02, unit: '%' }
        ],
        timestamp: new Date().toISOString()
      })
    );
  }),

  // Generate CRUD handlers for main resources
  ...createCrudHandlers('customers', factories.Customer),
  ...createCrudHandlers('users', factories.User),
  ...createCrudHandlers('tickets', factories.Ticket),
  ...createCrudHandlers('tenants', factories.Tenant),

  // Error simulation handlers
  http.get(`${API_BASE_URL}/test/error/:code`, async ({ params }) => {
    const code = parseInt(params.code);
    return HttpResponse.json(
      factories.ApiResponse.error(`Test error ${code}`, code),
      { status: code }
    );
  }),

  // Slow response simulation
  http.get(`${API_BASE_URL}/test/slow`, async () => {
    await new Promise(resolve => setTimeout(resolve, 2000));
    return HttpResponse.json(
      factories.ApiResponse.success({ message: 'Slow response completed' })
    );
  })
];

/**
 * Setup MSW server with DRY configuration
 */
const server = setupServer(...handlers);

/**
 * DRY utilities for test-specific mock modifications
 */
const mockUtils = {
  // Override specific handlers for individual tests
  useHandler(handler: any): void {
    server.use(handler);
  },

  // Mock authentication state
  mockAuthenticatedUser(user: any = createMockData.admin()): any {
    server.use(
      http.get(`${API_BASE_URL}/auth/me`, () => {
        return HttpResponse.json(
          factories.ApiResponse.success(user)
        );
      })
    );
    return user;
  },

  // Mock API errors
  mockApiError(endpoint: string, code: number = 500, message: string = 'Server Error'): void {
    server.use(
      http.get(`${API_BASE_URL}${endpoint}`, () => {
        return HttpResponse.json(
          factories.ApiResponse.error(message, code),
          { status: code }
        );
      })
    );
  },

  // Mock loading states
  mockSlowResponse(endpoint: string, delay: number = 1000): void {
    server.use(
      http.get(`${API_BASE_URL}${endpoint}`, async () => {
        await new Promise(resolve => setTimeout(resolve, delay));
        return HttpResponse.json(
          factories.ApiResponse.success({ delayed: true })
        );
      })
    );
  },

  // Reset to default handlers
  resetHandlers(): void {
    server.resetHandlers();
  }
};

export { server, mockUtils };
