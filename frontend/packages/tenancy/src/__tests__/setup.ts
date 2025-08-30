import '@testing-library/jest-dom';

// Mock console methods to avoid noise in tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is no longer supported')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Global test utilities
global.testUtils = {
  // Consistent test IDs
  getTestId: (id: string) => `[data-testid="${id}"]`,

  // Environment helpers
  isDevelopment: () => process.env.NODE_ENV === 'development',
  isTest: () => process.env.NODE_ENV === 'test',

  // Mock API responses
  mockApiSuccess: (data: any) => ({
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
  }),

  mockApiError: (message: string, status = 500) => {
    const error = new Error(message);
    (error as any).status = status;
    return error;
  },
};

// Extend Jest matchers
declare global {
  namespace jest {
    interface Matchers<R> {
      toHaveTestId(testId: string): R;
    }
  }

  var testUtils: {
    getTestId: (id: string) => string;
    isDevelopment: () => boolean;
    isTest: () => boolean;
    mockApiSuccess: (data: any) => any;
    mockApiError: (message: string, status?: number) => Error;
  };
}

// Custom matcher for test IDs
expect.extend({
  toHaveTestId(received, testId) {
    const pass = received.querySelector(`[data-testid="${testId}"]`) !== null;
    return {
      message: () =>
        pass
          ? `Expected element not to have test ID "${testId}"`
          : `Expected element to have test ID "${testId}"`,
      pass,
    };
  },
});
