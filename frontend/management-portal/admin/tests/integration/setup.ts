/**
 * Integration Test Setup
 * Additional setup specifically for integration tests
 */

import '@testing-library/jest-dom';

// Mock fetch for integration tests
global.fetch = jest.fn();

// Enhanced WebSocket mock for integration testing
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  public readyState: number = MockWebSocket.CONNECTING;
  public url: string;
  public protocol: string;

  private eventListeners: { [key: string]: Function[] } = {};

  constructor(url: string, protocols?: string | string[]) {
    this.url = url;
    this.protocol = Array.isArray(protocols) ? protocols[0] : protocols || '';

    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.dispatchEvent(new Event('open'));
    }, 100);
  }

  send(data: string): void {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock echo response
    setTimeout(() => {
      this.dispatchEvent(new MessageEvent('message', { data: data }));
    }, 50);
  }

  close(code?: number, reason?: string): void {
    this.readyState = MockWebSocket.CLOSED;
    this.dispatchEvent(new CloseEvent('close', { code, reason }));
  }

  addEventListener(type: string, listener: Function): void {
    if (!this.eventListeners[type]) {
      this.eventListeners[type] = [];
    }
    this.eventListeners[type].push(listener);
  }

  removeEventListener(type: string, listener: Function): void {
    if (this.eventListeners[type]) {
      this.eventListeners[type] = this.eventListeners[type].filter((l) => l !== listener);
    }
  }

  dispatchEvent(event: Event): boolean {
    const listeners = this.eventListeners[event.type] || [];
    listeners.forEach((listener) => listener(event));
    return true;
  }
}

// Set up WebSocket mock
Object.defineProperty(global, 'WebSocket', {
  value: MockWebSocket,
  configurable: true,
});

// Enhanced localStorage mock for integration tests
const localStorageMock = (() => {
  let store: { [key: string]: string } = {};

  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    key: jest.fn((index: number) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    }),
    get length() {
      return Object.keys(store).length;
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Enhanced sessionStorage mock
const sessionStorageMock = (() => {
  let store: { [key: string]: string } = {};

  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    key: jest.fn((index: number) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    }),
    get length() {
      return Object.keys(store).length;
    },
  };
})();

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock Notification API for integration tests
Object.defineProperty(window, 'Notification', {
  value: {
    permission: 'default' as NotificationPermission,
    requestPermission: jest.fn().mockResolvedValue('granted' as NotificationPermission),
  },
  configurable: true,
});

// Mock Performance API for integration tests
Object.defineProperty(window, 'performance', {
  value: {
    now: jest.fn(() => Date.now()),
    mark: jest.fn(),
    measure: jest.fn(),
    getEntriesByType: jest.fn(() => []),
    getEntriesByName: jest.fn(() => []),
    clearMarks: jest.fn(),
    clearMeasures: jest.fn(),
  },
  configurable: true,
});

// Mock Navigator API for PWA testing
Object.defineProperty(navigator, 'serviceWorker', {
  value: {
    register: jest.fn().mockResolvedValue({
      installing: null,
      waiting: null,
      active: {
        postMessage: jest.fn(),
      },
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    }),
    ready: jest.fn().mockResolvedValue({
      installing: null,
      waiting: null,
      active: {
        postMessage: jest.fn(),
      },
      pushManager: {
        subscribe: jest.fn().mockResolvedValue({
          endpoint: 'https://example.com/push',
          keys: {
            p256dh: 'test-key',
            auth: 'test-auth',
          },
        }),
        getSubscription: jest.fn().mockResolvedValue(null),
      },
    }),
    getRegistration: jest.fn().mockResolvedValue(null),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  },
  configurable: true,
});

// Enhanced Canvas mock for fingerprinting tests
HTMLCanvasElement.prototype.getContext = jest.fn().mockReturnValue({
  fillText: jest.fn(),
  measureText: jest.fn().mockReturnValue({ width: 100 }),
  fillRect: jest.fn(),
  clearRect: jest.fn(),
  getImageData: jest.fn().mockReturnValue({
    data: new Uint8ClampedArray(400), // 10x10 canvas
  }),
});

HTMLCanvasElement.prototype.toDataURL = jest
  .fn()
  .mockReturnValue(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
  );

// Mock console methods for cleaner test output
const originalConsoleWarn = console.warn;
const originalConsoleError = console.error;

console.warn = jest.fn((message, ...args) => {
  // Suppress known test warnings
  if (
    typeof message === 'string' &&
    (message.includes('Warning: ReactDOMTestUtils.act') ||
      message.includes('Warning: An invalid form control'))
  ) {
    return;
  }
  originalConsoleWarn.call(console, message, ...args);
});

console.error = jest.fn((message, ...args) => {
  // Suppress known test errors
  if (
    typeof message === 'string' &&
    (message.includes('Error: Not implemented: navigation') ||
      message.includes('Error: Not implemented: window.scrollTo'))
  ) {
    return;
  }
  originalConsoleError.call(console, message, ...args);
});

// Global test utilities
declare global {
  namespace NodeJS {
    interface Global {
      TEST_API_BASE_URL: string;
      TEST_TIMEOUT: number;
    }
  }
}

// Set test environment variables
// process.env.NODE_ENV is read-only in test environment
process.env.NEXT_PUBLIC_APP_VERSION = '1.0.0-test';
process.env.INTEGRATION_TEST_API_URL = 'http://localhost:8000';

// Global test configuration
(global as any).TEST_API_BASE_URL = 'http://localhost:8000';
(global as any).TEST_TIMEOUT = 30000;

// Global setup for integration tests
beforeAll(() => {
  // Initialize any global test state
  console.log('🧪 Starting Integration Tests...');
});

afterAll(() => {
  // Cleanup global test state
  console.log('✅ Integration Tests Complete');
});

beforeEach(() => {
  // Reset mocks before each test
  jest.clearAllMocks();

  // Clear storage before each test
  localStorage.clear();
  sessionStorage.clear();

  // Reset fetch mock
  if (jest.isMockFunction(global.fetch)) {
    (global.fetch as jest.Mock).mockReset();
  } else {
    global.fetch = jest.fn();
  }
});

afterEach(() => {
  // Cleanup after each test
  jest.restoreAllMocks();
});

// Export utilities for use in tests
export const integrationTestUtils = {
  mockSuccessfulAuth: () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        user: { id: 'test-user', email: 'test@example.com' },
        token: 'mock-jwt-token',
      }),
    });
  },

  mockFailedAuth: () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({
        error: 'Invalid credentials',
      }),
    });
  },

  mockApiError: (status = 500, message = 'Internal Server Error') => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error(message));
  },

  simulateNetworkDelay: (delay = 1000) => {
    (global.fetch as jest.Mock).mockImplementationOnce(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                status: 200,
                json: async () => ({}),
              }),
            delay
          )
        )
    );
  },
};
