/* eslint-disable @typescript-eslint/no-require-imports */
import { server } from './__mocks__/server';

const { http, HttpResponse } = require('msw');

/**
 * Jest setup for integration tests
 * Follows backend pattern for comprehensive integration testing
 */

// Extended timeout for integration tests
jest.setTimeout(30000);

// Mock external dependencies that shouldn't be called in integration tests
jest.mock('next/font/google', () => ({
  // biome-ignore lint/style/useNamingConvention: Font name
  Inter: () => ({
    style: {
      fontFamily: 'Inter, sans-serif',
    },
  }),
}));

// Mock analytics/tracking services
jest.mock('./utils/analytics', () => ({
  track: jest.fn(),
  identify: jest.fn(),
  page: jest.fn(),
  reset: jest.fn(),
  analytics: {
    track: jest.fn(),
    identify: jest.fn(),
    page: jest.fn(),
    reset: jest.fn(),
  },
}));

// Mock payment services (conditionally - only if they exist)
try {
  jest.mock('@stripe/stripe-js', () => ({
    loadStripe: jest.fn(() =>
      Promise.resolve({
        confirmCardPayment: jest.fn(),
        createPaymentMethod: jest.fn(),
      })
    ),
  }));
} catch (_error) {
  // Stripe module not available, skip mocking
}

// Enhanced MSW server for integration tests
beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'error', // Fail tests on unhandled requests
  });
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});

// Test database/state management utilities
global.integrationUtils = {
  // Simulate API delays
  withDelay: (handler, delay = 100) => {
    return async (...args) => {
      await new Promise((resolve) => setTimeout(resolve, delay));
      return handler(...args);
    };
  },

  // Create test data factories (following backend pattern)
  factories: {
    customer: (
      overrides = {
        /* empty */
      }
    ) => ({
      id: `cust-${Date.now()}`,
      name: 'Test Customer',
      email: 'test@customer.com',
      plan: 'business_pro',
      status: 'active',
      mrr: 79.99,
      tenant: 'tenant-123',
      // biome-ignore lint/style/useNamingConvention: API field
      created_at: new Date().toISOString(),
      ...overrides,
    }),

    service: (
      overrides = {
        /* empty */
      }
    ) => ({
      id: `service-${Date.now()}`,
      name: 'Internet Service',
      type: 'internet',
      status: 'active',
      // biome-ignore lint/style/useNamingConvention: API field
      speed_down: 100,
      // biome-ignore lint/style/useNamingConvention: API field
      speed_up: 20,
      // biome-ignore lint/style/useNamingConvention: API field
      monthly_price: 79.99,
      ...overrides,
    }),

    invoice: (
      overrides = {
        /* empty */
      }
    ) => ({
      id: `inv-${Date.now()}`,
      number: `INV-${Date.now()}`,
      amount: 79.99,
      status: 'pending',
      // biome-ignore lint/style/useNamingConvention: API field
      due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      // biome-ignore lint/style/useNamingConvention: API field
      created_at: new Date().toISOString(),
      ...overrides,
    }),

    user: (
      overrides = {
        /* empty */
      }
    ) => ({
      id: `user-${Date.now()}`,
      name: 'Test User',
      email: 'test@user.com',
      role: 'customer',
      tenant: 'tenant-123',
      // biome-ignore lint/style/useNamingConvention: API field
      created_at: new Date().toISOString(),
      ...overrides,
    }),
  },

  // Error simulation utilities
  simulateErrors: {
    networkError: () => {
      server.use(
        http.get('*', () => {
          return HttpResponse.error();
        })
      );
    },

    serverError: (status = 500) => {
      server.use(
        http.get('*', () => {
          return HttpResponse.json({ message: 'Server Error' }, { status });
        })
      );
    },

    authError: () => {
      server.use(
        http.get('/api/v1/auth/*', () => {
          return HttpResponse.json({ message: 'Unauthorized' }, { status: 401 });
        })
      );
    },
  },

  // State management helpers
  setupAuthenticatedUser: (
    user = {
      /* empty */
    }
  ) => {
    const mockUser = global.integrationUtils.factories.user(user);
    localStorage.setItem('auth-token', 'mock-jwt-token');
    localStorage.setItem('user', JSON.stringify(mockUser));
    return mockUser;
  },

  clearAuth: () => {
    localStorage.removeItem('auth-token');
    localStorage.removeItem('user');
  },
};
