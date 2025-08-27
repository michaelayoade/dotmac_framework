/**
 * Jest Test Setup
 * Global test configuration and environment setup
 */

import '@testing-library/jest-dom';
import 'jest-canvas-mock';
import React from 'react';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
    };
  },
  usePathname() {
    return '/dashboard';
  },
  useSearchParams() {
    return new URLSearchParams();
  },
}));

// Mock Next.js image component
jest.mock('next/image', () => ({
  __esModule: true,
  default: ({ src, alt, ...props }: any) => {
    return React.createElement('img', { src, alt, ...props });
  },
}));

// Mock Next.js link component
jest.mock('next/link', () => ({
  __esModule: true,
  default: ({ children, href, ...props }: any) => {
    return React.createElement('a', { href, ...props }, children);
  },
}));

// Mock fetch API
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
});
window.IntersectionObserver = mockIntersectionObserver;

// Mock ResizeObserver
const mockResizeObserver = jest.fn();
mockResizeObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
});
window.ResizeObserver = mockResizeObserver;

// Mock console methods for cleaner test output
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (
        args[0].includes('Warning: ReactDOM.render is no longer supported') ||
        args[0].includes('Warning: Each child in a list should have a unique "key" prop') ||
        args[0].includes('act(...) is not supported in production builds')
      )
    ) {
      return;
    }
    originalError.call(console, ...args);
  };

  console.warn = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (
        args[0].includes('componentWillReceiveProps') ||
        args[0].includes('componentWillUpdate')
      )
    ) {
      return;
    }
    originalWarn.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock crypto API
const mockCrypto = {
  randomUUID: jest.fn(() => 'mock-uuid-1234-5678-9012'),
  getRandomValues: jest.fn((array: any) => {
    for (let i = 0; i < array.length; i++) {
      array[i] = Math.floor(Math.random() * 256);
    }
    return array;
  }),
};
Object.defineProperty(window, 'crypto', {
  value: mockCrypto,
});

// Mock performance API
const mockPerformance = {
  now: jest.fn(() => Date.now()),
  mark: jest.fn(),
  measure: jest.fn(),
  getEntriesByType: jest.fn(() => []),
  getEntriesByName: jest.fn(() => []),
  clearMarks: jest.fn(),
  clearMeasures: jest.fn(),
};
Object.defineProperty(window, 'performance', {
  value: mockPerformance,
});

// Mock URL constructor
global.URL = class URL {
  constructor(public href: string) {}
  get hostname() {
    return 'localhost';
  }
  get origin() {
    return 'http://localhost:3003';
  }
  get pathname() {
    return '/';
  }
  get search() {
    return '';
  }
  get hash() {
    return '';
  }
} as any;

// Mock AbortSignal.timeout for API client tests
if (!AbortSignal.timeout) {
  AbortSignal.timeout = jest.fn((timeout: number) => {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), timeout);
    return controller.signal;
  });
}

// Test utilities
export const testUtils = {
  // Reset all mocks between tests
  resetMocks: () => {
    jest.clearAllMocks();
    mockFetch.mockReset();
    localStorageMock.getItem.mockReset();
    localStorageMock.setItem.mockReset();
    localStorageMock.removeItem.mockReset();
    localStorageMock.clear.mockReset();
    sessionStorageMock.getItem.mockReset();
    sessionStorageMock.setItem.mockReset();
    sessionStorageMock.removeItem.mockReset();
    sessionStorageMock.clear.mockReset();
  },

  // Mock successful fetch response
  mockFetchSuccess: (data: any, status = 200) => {
    mockFetch.mockResolvedValueOnce({
      ok: status >= 200 && status < 300,
      status,
      json: async () => data,
      text: async () => JSON.stringify(data),
      headers: new Headers({ 'content-type': 'application/json' }),
    });
  },

  // Mock fetch error
  mockFetchError: (error: string, status = 500) => {
    mockFetch.mockRejectedValueOnce(new Error(error));
  },

  // Mock localStorage
  mockLocalStorage: (items: Record<string, string> = {}) => {
    localStorageMock.getItem.mockImplementation((key: string) => items[key] || null);
    localStorageMock.setItem.mockImplementation((key: string, value: string) => {
      items[key] = value;
    });
    localStorageMock.removeItem.mockImplementation((key: string) => {
      delete items[key];
    });
    localStorageMock.clear.mockImplementation(() => {
      Object.keys(items).forEach(key => delete items[key]);
    });
  },

  // Wait for async operations
  waitFor: (ms: number = 0) => new Promise(resolve => setTimeout(resolve, ms)),

  // Create mock user data
  createMockUser: (overrides = {}) => ({
    id: 'user-123',
    email: 'test@example.com',
    name: 'Test User',
    role: 'admin',
    tenant_id: 'tenant-123',
    permissions: ['read', 'write'],
    last_login: new Date().toISOString(),
    ...overrides,
  }),

  // Create mock tenant data
  createMockTenant: (overrides = {}) => ({
    id: 'tenant-123',
    name: 'test-tenant',
    display_name: 'Test Tenant',
    slug: 'test-tenant',
    status: 'active' as const,
    tier: 'standard',
    primary_color: '#3B82F6',
    ...overrides,
  }),

  // Create mock API response
  createMockApiResponse: (data: any, success = true) => ({
    success,
    data,
    message: success ? 'Success' : 'Error',
    ...(success ? {} : { error: 'Mock error' }),
  }),
};

// Global test setup
beforeEach(() => {
  testUtils.resetMocks();
});

// Add custom matchers
expect.extend({
  toBeValidEmail(received: string) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const pass = emailRegex.test(received);
    
    if (pass) {
      return {
        message: () => `expected ${received} not to be a valid email`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be a valid email`,
        pass: false,
      };
    }
  },

  toHaveValidationError(received: any, field: string) {
    const hasError = received?.errors && received.errors[field];
    
    if (hasError) {
      return {
        message: () => `expected not to have validation error for field ${field}`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected to have validation error for field ${field}`,
        pass: false,
      };
    }
  },
});