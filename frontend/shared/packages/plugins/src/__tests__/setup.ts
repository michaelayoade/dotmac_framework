import '@testing-library/jest-dom';

// Mock API client
jest.mock('@dotmac/headless', () => ({
  useApiClient: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  })),
}));

// Mock date-fns to avoid timezone issues in tests
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '2 minutes ago'),
  format: jest.fn(() => '2023-01-01'),
}));

// Global test setup
beforeEach(() => {
  // Clear all mocks before each test
  jest.clearAllMocks();
});
