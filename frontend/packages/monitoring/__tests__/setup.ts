/**
 * Test setup for @dotmac/monitoring package
 * Configures testing environment for monitoring components and utilities
 */

import '@testing-library/jest-dom';

// Mock Sentry for monitoring tests
const mockSentryInit = jest.fn();
const mockCaptureException = jest.fn();
const mockCaptureMessage = jest.fn();
const mockWithScope = jest.fn();
const mockSetTag = jest.fn();
const mockSetUser = jest.fn();
const mockSetContext = jest.fn();
const mockAddBreadcrumb = jest.fn();

jest.mock('@sentry/react', () => ({
  init: mockSentryInit,
  captureException: mockCaptureException,
  captureMessage: mockCaptureMessage,
  withScope: mockWithScope.mockImplementation((callback) => {
    const scope = {
      setTag: mockSetTag,
      setUser: mockSetUser,
      setContext: mockSetContext,
      addBreadcrumb: mockAddBreadcrumb,
      setLevel: jest.fn(),
      setFingerprint: jest.fn()
    };
    callback(scope);
  }),
  Severity: {
    Error: 'error',
    Warning: 'warning',
    Info: 'info',
    Debug: 'debug'
  },
  ErrorBoundary: jest.fn(({ children }) => children),
  withErrorBoundary: jest.fn((component) => component),
  getCurrentHub: jest.fn(() => ({
    getClient: jest.fn(() => ({
      getOptions: jest.fn(() => ({}))
    }))
  })),
  configureScope: jest.fn()
}));

// Mock @sentry/tracing for performance monitoring
jest.mock('@sentry/tracing', () => ({
  BrowserTracing: jest.fn(),
  startTransaction: jest.fn(() => ({
    setTag: jest.fn(),
    setData: jest.fn(),
    finish: jest.fn()
  })),
  getCurrentTransaction: jest.fn()
}));

// Mock performance API
global.performance = global.performance || {};
global.performance.now = global.performance.now || (() => Date.now());
global.performance.mark = global.performance.mark || jest.fn();
global.performance.measure = global.performance.measure || jest.fn();
global.performance.getEntriesByType = global.performance.getEntriesByType || jest.fn(() => []);
global.performance.getEntriesByName = global.performance.getEntriesByName || jest.fn(() => []);
global.performance.clearMarks = global.performance.clearMarks || jest.fn();
global.performance.clearMeasures = global.performance.clearMeasures || jest.fn();

// Mock PerformanceObserver for Web Vitals
global.PerformanceObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
  takeRecords: jest.fn(() => [])
}));

// Mock fetch for health checks and API monitoring
global.fetch = jest.fn();

// Mock WebSocket for real-time monitoring
global.WebSocket = jest.fn().mockImplementation(() => ({
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  send: jest.fn(),
  close: jest.fn(),
  readyState: 1,
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3
}));

// Mock localStorage and sessionStorage for monitoring data
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn()
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn()
};
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock });

// Mock console methods to control test output
const originalError = console.error;
const originalWarn = console.warn;
const originalLog = console.log;

beforeEach(() => {
  // Clear all mocks
  jest.clearAllMocks();

  // Reset mock implementations
  mockSentryInit.mockClear();
  mockCaptureException.mockClear();
  mockCaptureMessage.mockClear();
  mockWithScope.mockClear();
  mockSetTag.mockClear();
  mockSetUser.mockClear();
  mockSetContext.mockClear();
  mockAddBreadcrumb.mockClear();

  // Reset storage mocks
  localStorageMock.clear.mockClear();
  localStorageMock.getItem.mockClear();
  localStorageMock.setItem.mockClear();
  localStorageMock.removeItem.mockClear();

  sessionStorageMock.clear.mockClear();
  sessionStorageMock.getItem.mockClear();
  sessionStorageMock.setItem.mockClear();
  sessionStorageMock.removeItem.mockClear();

  // Reset fetch mock
  (global.fetch as jest.Mock).mockClear();

  // Mock console methods (can be overridden in individual tests)
  console.error = jest.fn();
  console.warn = jest.fn();
  console.log = jest.fn();
});

afterEach(() => {
  // Restore console methods
  console.error = originalError;
  console.warn = originalWarn;
  console.log = originalLog;

  // Clear timers if any
  jest.clearAllTimers();
});

afterAll(() => {
  jest.restoreAllMocks();
});

// Helper functions for monitoring testing
export const mockLocalStorage = localStorageMock;
export const mockSessionStorage = sessionStorageMock;

export const mockFetchResponse = (data: any, status = 200, ok = true) => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: jest.fn().mockResolvedValueOnce(data),
    text: jest.fn().mockResolvedValueOnce(JSON.stringify(data)),
    headers: new Map([
      ['content-type', 'application/json']
    ])
  });
};

export const mockFetchError = (error: Error) => {
  (global.fetch as jest.Mock).mockRejectedValueOnce(error);
};

// Sentry mock helpers
export const mockSentryCapture = {
  exception: mockCaptureException,
  message: mockCaptureMessage,
  withScope: mockWithScope,
  setTag: mockSetTag,
  setUser: mockSetUser,
  setContext: mockSetContext,
  addBreadcrumb: mockAddBreadcrumb
};

export const mockPerformanceEntry = (type: string, name: string, duration = 100) => ({
  name,
  entryType: type,
  startTime: performance.now(),
  duration,
  responseStart: performance.now() + 10,
  responseEnd: performance.now() + duration
});

export const mockWebVitalsEntry = (name: string, value: number) => ({
  name,
  value,
  rating: value < 100 ? 'good' : value < 300 ? 'needs-improvement' : 'poor',
  delta: value,
  id: `v1-${Date.now()}-${Math.random()}`,
  entries: []
});

// Mock monitoring configuration for different portals
export const createMockMonitoringConfig = (portal: string, overrides = {}) => ({
  portal,
  sentry: {
    enabled: true,
    dsn: 'mock-dsn',
    environment: 'test',
    debug: portal === 'management-admin' || portal === 'management-reseller',
    tracesSampleRate: portal === 'tenant-portal' ? 0.1 : 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0
  },
  performance: {
    enabled: true,
    trackWebVitals: true,
    trackUserInteractions: portal !== 'customer' && portal !== 'tenant-portal',
    reportThresholds: {
      cls: 0.1,
      fid: 100,
      lcp: 2500
    }
  },
  health: {
    enabled: true,
    interval: portal === 'management-admin' ? 15000 :
              portal === 'management-reseller' ? 20000 :
              portal === 'tenant-portal' ? 60000 : 30000,
    timeout: portal === 'technician' ? 8000 :
             portal === 'management-reseller' ? 7000 : 5000,
    retries: 3,
    endpoints: [`/api/${portal === 'admin' ? 'admin' :
                      portal === 'management-reseller' ? 'management-reseller' :
                      portal === 'tenant-portal' ? 'tenant' : portal}/health`]
  },
  validation: {
    enabled: true,
    strictMode: portal === 'management-admin' || portal === 'reseller' || portal === 'management-reseller',
    validateSchemas: true,
    validatePermissions: portal !== 'customer' && portal !== 'tenant-portal'
  },
  ...overrides
});

// Mock error objects for testing
export const createMockError = (message: string, type?: string) => {
  const error = new Error(message);
  error.name = type || 'Error';
  error.stack = `${error.name}: ${message}\n    at TestComponent\n    at ErrorBoundary`;
  return error;
};

// Mock health check response
export const createMockHealthResponse = (status: 'healthy' | 'unhealthy' | 'degraded' = 'healthy') => ({
  status,
  timestamp: new Date().toISOString(),
  version: '1.0.0',
  uptime: 3600000,
  services: {
    database: status,
    cache: status,
    external_api: status
  },
  metrics: {
    responseTime: status === 'healthy' ? 150 : 800,
    memoryUsage: 0.65,
    cpuUsage: 0.25
  }
});

// Custom Jest matchers for monitoring
declare global {
  namespace jest {
    interface Matchers<R> {
      toHaveBeenCapturedBySentry(): R;
      toHavePerformanceEntry(entryType: string): R;
      toHaveHealthStatus(status: string): R;
      toBeWithinPerformanceThreshold(threshold: number): R;
    }
  }
}

expect.extend({
  toHaveBeenCapturedBySentry(received: any) {
    const wasCaptured = mockCaptureException.mock.calls.some(call =>
      call[0] === received || call[0].message === received?.message
    );

    return {
      message: () =>
        wasCaptured
          ? `Expected error not to be captured by Sentry`
          : `Expected error to be captured by Sentry`,
      pass: wasCaptured,
    };
  },

  toHavePerformanceEntry(received: any, entryType: string) {
    const hasEntry = received && received.entryType === entryType;

    return {
      message: () =>
        hasEntry
          ? `Expected not to have performance entry of type "${entryType}"`
          : `Expected to have performance entry of type "${entryType}"`,
      pass: hasEntry,
    };
  },

  toHaveHealthStatus(received: any, status: string) {
    const hasStatus = received && received.status === status;

    return {
      message: () =>
        hasStatus
          ? `Expected health check not to have status "${status}"`
          : `Expected health check to have status "${status}"`,
      pass: hasStatus,
    };
  },

  toBeWithinPerformanceThreshold(received: number, threshold: number) {
    const isWithin = received <= threshold;

    return {
      message: () =>
        isWithin
          ? `Expected ${received} not to be within threshold ${threshold}`
          : `Expected ${received} to be within threshold ${threshold}`,
      pass: isWithin,
    };
  }
});

// Mock environment variables
Object.defineProperty(process.env, 'NODE_ENV', {
  value: 'test',
  writable: true
});

// Mock timers for interval-based monitoring
jest.useFakeTimers();

// Export all mocks for easy access in tests
export {
  mockSentryInit,
  mockCaptureException,
  mockCaptureMessage,
  mockWithScope,
  mockSetTag,
  mockSetUser,
  mockSetContext,
  mockAddBreadcrumb
};
