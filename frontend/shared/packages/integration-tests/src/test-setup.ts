/**
 * Integration Test Setup Configuration
 * Global test setup and mocks for component integration tests
 */

import '@testing-library/jest-dom';
import 'jest-environment-jsdom';

// Global mocks for browser APIs
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
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
global.IntersectionObserver = jest.fn().mockImplementation((callback) => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
  root: null,
  rootMargin: '',
  thresholds: [],
}));

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation((callback) => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock WebSocket
global.WebSocket = jest.fn().mockImplementation((url) => ({
  url,
  readyState: WebSocket.OPEN,
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  onopen: null,
  onclose: null,
  onmessage: null,
  onerror: null,
}));

// Mock fetch for API calls
global.fetch = jest.fn();

// Mock console methods to reduce noise in tests
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: ReactDOM.render is no longer supported') ||
        args[0].includes('Warning: An invalid form control'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };

  console.warn = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('componentWillReceiveProps') || args[0].includes('componentWillUpdate'))
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

// Clear all mocks after each test
afterEach(() => {
  jest.clearAllMocks();

  // Reset fetch mock
  (global.fetch as jest.Mock).mockReset();
});

// Mock environment variables
process.env.NODE_ENV = 'test';
process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:3001';
process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8080/ws';

// Extend Jest matchers
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeVisible(): R;
      toHaveAccessibleName(name: string): R;
      toHaveAccessibleDescription(description: string): R;
    }
  }
}

// Helper function to create mock API responses
export const createMockApiResponse = <T>(data: T, delay = 0): Promise<T> => {
  return new Promise((resolve) => {
    setTimeout(() => resolve(data), delay);
  });
};

// Helper function to create mock API error
export const createMockApiError = (message: string, status = 500, delay = 0): Promise<never> => {
  return new Promise((_, reject) => {
    setTimeout(() => {
      const error = new Error(message);
      (error as any).status = status;
      reject(error);
    }, delay);
  });
};

// Helper to simulate WebSocket messages
export const simulateWebSocketMessage = (data: any, socket?: any) => {
  const message = { data: JSON.stringify(data) };
  if (socket && socket.onmessage) {
    socket.onmessage(message);
  }
  return message;
};

// Helper to create test query client
import { QueryClient } from '@tanstack/react-query';

export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

global.localStorage = localStorageMock as any;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

global.sessionStorage = sessionStorageMock as any;
