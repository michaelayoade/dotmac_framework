/**
 * Enhanced Test Setup for Reseller Portal
 * 
 * Provides comprehensive testing utilities including:
 * - Accessibility testing with jest-axe
 * - Performance testing utilities
 * - Security testing helpers
 * - Mock data management
 * - Custom matchers
 */

import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';
import { toHaveNoViolations } from 'jest-axe';
import 'whatwg-fetch';

// Configure testing library
configure({
  testIdAttribute: 'data-testid',
  asyncUtilTimeout: 5000,
  computedStyleSupportsPseudoElements: true,
});

// Add custom jest matchers
expect.extend(toHaveNoViolations);

// Security testing matchers
expect.extend({
  toBeSecureInput(received) {
    const dangerousPatterns = [
      /<script/i,
      /javascript:/i,
      /vbscript:/i,
      /on\w+=/i,
      /data:/i,
    ];

    const hasDangerousPattern = dangerousPatterns.some(pattern => 
      pattern.test(received)
    );

    return {
      message: () => `Expected input to be secure, but found dangerous patterns`,
      pass: !hasDangerousPattern,
    };
  },

  toHaveValidCSRFProtection(received) {
    const hasCSRFToken = received.headers && (
      received.headers['x-csrf-token'] ||
      received.headers['X-CSRF-Token'] ||
      received.headers['csrf-token']
    );

    return {
      message: () => `Expected request to have CSRF token in headers`,
      pass: !!hasCSRFToken,
    };
  },

  toHaveSecurityHeaders(received) {
    const requiredHeaders = [
      'content-security-policy',
      'x-frame-options',
      'x-content-type-options',
      'referrer-policy',
    ];

    const missingHeaders = requiredHeaders.filter(header => 
      !received.headers?.[header]
    );

    return {
      message: () => `Expected response to have security headers. Missing: ${missingHeaders.join(', ')}`,
      pass: missingHeaders.length === 0,
    };
  },
});

// Performance testing utilities
global.measurePerformance = (fn, label = 'performance-test') => {
  const start = performance.now();
  const result = fn();
  const end = performance.now();
  
  if (result && typeof result.then === 'function') {
    return result.then(r => {
      console.log(`${label}: ${end - start}ms`);
      return r;
    });
  }
  
  console.log(`${label}: ${end - start}ms`);
  return result;
};

// Mock performance API if not available
if (typeof performance === 'undefined') {
  global.performance = {
    now: () => Date.now(),
    mark: jest.fn(),
    measure: jest.fn(),
    getEntriesByName: jest.fn(() => []),
    getEntriesByType: jest.fn(() => []),
  };
}

// Mock IntersectionObserver for component visibility testing
global.IntersectionObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
  root: null,
  rootMargin: '',
  thresholds: [],
}));

// Mock ResizeObserver
global.ResizeObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock geolocation for territory testing
const mockGeolocation = {
  getCurrentPosition: jest.fn((success, error) => {
    success({
      coords: {
        latitude: 40.7128,
        longitude: -74.0060,
        accuracy: 10,
      },
      timestamp: Date.now(),
    });
  }),
  watchPosition: jest.fn(),
  clearWatch: jest.fn(),
};

Object.defineProperty(global.navigator, 'geolocation', {
  value: mockGeolocation,
  writable: true,
});

// Mock console methods in test environment to reduce noise
const originalConsole = { ...console };
beforeEach(() => {
  jest.spyOn(console, 'warn').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
  jest.spyOn(console, 'log').mockImplementation(() => {});
});

afterEach(() => {
  console.warn.mockRestore?.();
  console.error.mockRestore?.();
  console.log.mockRestore?.();
});

// Global test utilities
global.testUtils = {
  // Accessibility testing helper
  async checkA11y(container, options = {}) {
    const { axe } = await import('jest-axe');
    const results = await axe(container, {
      rules: {
        'color-contrast': { enabled: true },
        'keyboard-navigation': { enabled: true },
        'aria-labels': { enabled: true },
        'focus-management': { enabled: true },
      },
      ...options,
    });
    expect(results).toHaveNoViolations();
  },

  // Performance testing helper
  async expectPerformance(fn, maxTime = 100) {
    const start = performance.now();
    await fn();
    const duration = performance.now() - start;
    expect(duration).toBeLessThan(maxTime);
  },

  // Security testing helper
  expectSecureComponent(component) {
    const html = component.container.innerHTML;
    expect(html).toBeSecureInput();
  },

  // Mock data helper
  withMockData(mockData, testFn) {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';
    
    try {
      return testFn(mockData);
    } finally {
      process.env.NODE_ENV = originalEnv;
    }
  },

  // API mock helper
  mockApiCall(url, response, options = {}) {
    return jest.fn().mockImplementation(() => 
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(response),
        headers: {
          'content-type': 'application/json',
          'x-csrf-token': 'mock-csrf-token',
          ...options.headers,
        },
        ...options,
      })
    );
  },

  // Component testing helper
  async testComponentLifecycle(Component, props = {}) {
    const { render, unmount } = await import('@testing-library/react');
    const { container } = render(<Component {...props} />);
    
    // Test initial render
    expect(container).toBeInTheDocument();
    
    // Test accessibility
    await this.checkA11y(container);
    
    // Test unmount
    unmount();
  },

  // Form testing helper
  async testFormSubmission(form, validData, invalidData) {
    const { fireEvent, waitFor } = await import('@testing-library/react');
    
    // Test valid submission
    Object.entries(validData).forEach(([field, value]) => {
      const input = form.getByLabelText(new RegExp(field, 'i'));
      fireEvent.change(input, { target: { value } });
    });
    
    fireEvent.submit(form.getByRole('form'));
    await waitFor(() => {
      expect(form.queryByText(/error/i)).not.toBeInTheDocument();
    });

    // Test invalid submission
    Object.entries(invalidData).forEach(([field, value]) => {
      const input = form.getByLabelText(new RegExp(field, 'i'));
      fireEvent.change(input, { target: { value } });
    });
    
    fireEvent.submit(form.getByRole('form'));
    await waitFor(() => {
      expect(form.getByText(/error/i)).toBeInTheDocument();
    });
  },
};

// Error boundary for test errors
global.ErrorBoundary = ({ children, onError = () => {} }) => {
  try {
    return children;
  } catch (error) {
    onError(error);
    return <div>Error occurred during test</div>;
  }
};

// Network request mocking
beforeEach(() => {
  // Mock fetch globally
  global.fetch = jest.fn();
  
  // Mock localStorage
  const localStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
    length: 0,
    key: jest.fn(),
  };
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
    writable: true,
  });

  // Mock sessionStorage
  Object.defineProperty(window, 'sessionStorage', {
    value: { ...localStorageMock },
    writable: true,
  });
});

afterEach(() => {
  // Clear all mocks
  jest.clearAllMocks();
  
  // Reset fetch mock
  if (global.fetch && global.fetch.mockClear) {
    global.fetch.mockClear();
  }
});

// Global error handler for unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // In test environment, we want to know about these
  throw new Error(`Unhandled promise rejection: ${reason}`);
});

// Increase test timeout for complex integration tests
jest.setTimeout(30000);