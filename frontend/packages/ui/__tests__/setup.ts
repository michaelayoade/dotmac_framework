/**
 * Test setup for @dotmac/ui package
 * Configures testing environment for UI components
 */

import '@testing-library/jest-dom';

// Mock ResizeObserver which might be used by components
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock IntersectionObserver which might be used by components
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock window.matchMedia for responsive components
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

// Mock performance.now for performance tests
global.performance = global.performance || {};
global.performance.now = global.performance.now || (() => Date.now());

// Mock requestAnimationFrame for animations
global.requestAnimationFrame = jest.fn((callback) => setTimeout(callback, 16));
global.cancelAnimationFrame = jest.fn((id) => clearTimeout(id));

// Mock CSS.supports for feature detection
global.CSS = global.CSS || {};
global.CSS.supports = global.CSS.supports || jest.fn(() => true);

// Suppress console warnings for tests unless they're actual errors
const originalWarn = console.warn;
const originalError = console.error;

beforeEach(() => {
  console.warn = jest.fn();
  console.error = jest.fn();
});

afterEach(() => {
  console.warn = originalWarn;
  console.error = originalError;
});

// Mock Radix UI primitives portal behavior for testing
const mockPortalContainer = document.createElement('div');
mockPortalContainer.setAttribute('id', 'radix-portal-container');
document.body.appendChild(mockPortalContainer);

// Add custom jest matchers if needed
expect.extend({
  toHaveValidPortalVariant(received: Element, variant: string) {
    const variantClasses = {
      admin: ['border-blue', 'bg-blue', 'text-blue'],
      customer: ['border-green', 'bg-green', 'text-green'],
      reseller: ['border-purple', 'bg-purple', 'text-purple'],
      technician: ['border-orange', 'bg-orange', 'text-orange'],
      management: ['border-slate', 'bg-slate', 'text-slate']
    };

    const expectedClasses = variantClasses[variant as keyof typeof variantClasses];
    if (!expectedClasses) {
      return {
        message: () => `Unknown variant: ${variant}`,
        pass: false,
      };
    }

    const hasVariantClasses = expectedClasses.some(className =>
      Array.from(received.classList).some(cls => cls.includes(className))
    );

    return {
      message: () =>
        hasVariantClasses
          ? `Expected element not to have ${variant} variant classes`
          : `Expected element to have ${variant} variant classes`,
      pass: hasVariantClasses,
    };
  },
});
