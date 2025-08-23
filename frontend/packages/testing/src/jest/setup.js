/**
 * Jest Setup for DotMac Testing Framework
 *
 * Configures Jest with testing utilities, matchers, and global setup
 */

// Import Jest DOM matchers
import '@testing-library/jest-dom';

// Import axe matchers
import { toHaveNoViolations } from 'jest-axe';

// Import custom matchers
import '../utils/matchers';

// Extend Jest expect with axe matchers
expect.extend(toHaveNoViolations);

// Global test configuration
global.TEST_CONFIG = {
  enableA11yTesting: true,
  enableSecurityTesting: true,
  enablePerformanceTesting: false,
  mockApis: true,
  logSecurityEvents: false,
};

// Mock IntersectionObserver for components that use it
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock ResizeObserver for components that use it
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock matchMedia for responsive components
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

// Mock window.performance for performance testing
if (!global.performance) {
  global.performance = {
    now: jest.fn(() => Date.now()),
    mark: jest.fn(),
    measure: jest.fn(),
    clearMarks: jest.fn(),
    clearMeasures: jest.fn(),
    getEntriesByName: jest.fn(() => []),
    getEntriesByType: jest.fn(() => []),
  };
}

// Mock crypto for security testing
if (!global.crypto) {
  global.crypto = {
    randomUUID: jest.fn(() => 'test-uuid'),
    getRandomValues: jest.fn((arr) => {
      for (let i = 0; i < arr.length; i++) {
        arr[i] = Math.floor(Math.random() * 256);
      }
      return arr;
    }),
  };
}

// Mock localStorage for storage testing
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn(),
};
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock });

// Console warning filter for known issues
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

console.error = (...args) => {
  // Filter out known warnings/errors that are expected in tests
  const message = args[0];
  if (typeof message === 'string') {
    // React warnings we can ignore in tests
    if (message.includes('Warning: ReactDOM.render is deprecated')) return;
    if (message.includes('Warning: componentWillReceiveProps has been renamed')) return;
    if (message.includes('act(() => { ... })')) return;
  }
  originalConsoleError(...args);
};

console.warn = (...args) => {
  const message = args[0];
  if (typeof message === 'string') {
    // Warnings we can ignore in tests
    if (message.includes('componentWillReceiveProps has been renamed')) return;
  }
  originalConsoleWarn(...args);
};

// Global test helpers
global.testUtils = {
  // Helper to wait for async operations
  waitForAsync: async (callback, timeout = 5000) => {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Async operation timed out')), timeout);

      callback()
        .then((result) => {
          clearTimeout(timer);
          resolve(result);
        })
        .catch((error) => {
          clearTimeout(timer);
          reject(error);
        });
    });
  },

  // Helper to mock component props
  createMockProps: (overrides = {}) => ({
    'data-testid': 'test-component',
    ...overrides,
  }),

  // Helper to create mock event handlers
  createMockHandlers: () => ({
    onClick: jest.fn(),
    onChange: jest.fn(),
    onSubmit: jest.fn(),
    onFocus: jest.fn(),
    onBlur: jest.fn(),
  }),
};

// Accessibility testing helpers
global.a11yUtils = {
  // Check if element has proper labeling
  hasProperLabeling: (element) => {
    return (
      element.hasAttribute('aria-label') ||
      element.hasAttribute('aria-labelledby') ||
      element.querySelector('label')
    );
  },

  // Check if interactive element is keyboard accessible
  isKeyboardAccessible: (element) => {
    return (
      element.hasAttribute('tabindex') ||
      ['button', 'a', 'input', 'select', 'textarea'].includes(element.tagName.toLowerCase())
    );
  },
};

// Security testing helpers
global.securityUtils = {
  // Check for dangerous patterns
  hasDangerousPatterns: (html) => {
    return /(<script|javascript:|on\w+\s*=|data:)/gi.test(html);
  },

  // Sanitize test input
  sanitizeInput: (input) => {
    return input
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;');
  },
};

// Performance testing helpers
global.perfUtils = {
  measureRenderTime: async (renderFunction) => {
    const start = performance.now();
    await renderFunction();
    const end = performance.now();
    return end - start;
  },

  measureMemoryUsage: () => {
    if ('memory' in performance) {
      return performance.memory.usedJSHeapSize;
    }
    return 0;
  },
};

// Setup test environment
beforeEach(() => {
  // Clear all mocks before each test
  jest.clearAllMocks();

  // Reset localStorage and sessionStorage
  localStorageMock.clear();
  sessionStorageMock.clear();

  // Reset console spies
  jest.clearAllTimers();
});

afterEach(() => {
  // Clean up after each test
  document.body.innerHTML = '';

  // Reset any global state
  if (global.TEST_STATE) {
    global.TEST_STATE = {};
  }
});

// Global error handler for unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Export configuration for use in tests
export const testConfig = global.TEST_CONFIG;
export const testUtils = global.testUtils;
export const a11yUtils = global.a11yUtils;
export const securityUtils = global.securityUtils;
export const perfUtils = global.perfUtils;
