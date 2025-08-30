/**
 * Global Jest setup - DRY test environment configuration.
 */

import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';
import { server } from '../mocks/server';

// Configure React Testing Library
configure({
  testIdAttribute: 'data-testid'
});

// Global test utilities
global.testUtils = {
  // Consistent test IDs
  getTestId: (id: string) => `[data-testid="${id}"]`,

  // Environment helpers
  isDevelopment: () => process.env.NODE_ENV === 'development',
  isCI: () => process.env.CI === 'true',

  // Async utilities
  waitFor: (ms: number) => new Promise(resolve => setTimeout(resolve, ms)),

  // Mock data generators
  generateId: () => `test-${Math.random().toString(36).substr(2, 9)}`,
  generateEmail: () => `test-${Date.now()}@example.com`
};

// MSW Setup (Mock Service Worker)
beforeAll(() => {
  // Start MSW server for API mocking
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  // Reset handlers after each test
  server.resetHandlers();

  // Clear all mocks
  jest.clearAllMocks();

  // Reset document body
  document.body.innerHTML = '';
});

afterAll(() => {
  // Clean up MSW
  server.close();
});

// Global error handling
const originalError = console.error;
beforeAll(() => {
  console.error = (...args) => {
    // Suppress specific React warnings in tests
    if (
      args[0]?.includes?.('Warning: ReactDOM.render is no longer supported') ||
      args[0]?.includes?.('Warning: componentWillReceiveProps has been renamed')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Mock IntersectionObserver (commonly needed)
global.IntersectionObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn()
}));

// Mock ResizeObserver
global.ResizeObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn()
}));

// Mock matchMedia
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
    dispatchEvent: jest.fn()
  }))
});

// Mock scrollTo
Object.defineProperty(window, 'scrollTo', {
  value: jest.fn(),
  writable: true
});
