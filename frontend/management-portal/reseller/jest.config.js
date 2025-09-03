const nextJest = require('next/jest');

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: './',
});

// Master Jest config - runs all test types by default
// Use specific configs (jest.unit.config.js, jest.integration.config.js, etc.) for targeted testing
const customJestConfig = {
  displayName: 'All Tests',
  // Add more setup options before each test is run
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  // Test environment
  testEnvironment: 'jest-environment-jsdom',

  // Module paths
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/(.*)$': '<rootDir>/../../packages/$1/src',
  },

  // Test patterns
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.{test,spec}.{js,jsx,ts,tsx}',
    '<rootDir>/tests/**/*.{test,spec}.{js,jsx,ts,tsx}',
  ],

  // Coverage configuration
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/index.{js,jsx,ts,tsx}',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/app/**', // Exclude Next.js app directory
    '!src/middleware.ts',
  ],

  coverageReporters: ['text', 'lcov', 'html', 'json-summary'],

  // Custom reporters
  reporters: ['default', ['<rootDir>/tests/coverage-reporter.js', {}]],
  coverageDirectory: 'coverage',

  // Coverage thresholds
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },

  // Transform ignore patterns
  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.mjs$|@dotmac/.*|recharts|react-window|react-error-boundary))',
  ],

  // Additional transform patterns for ESM modules
  extensionsToTreatAsEsm: ['.ts', '.tsx'],

  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }],
  },

  // Module directories
  moduleDirectories: ['node_modules', '<rootDir>/src'],

  // Setup files
  setupFiles: ['<rootDir>/jest.env.js'],

  // Test timeout
  testTimeout: 30000,

  // Clear mocks
  clearMocks: true,
  restoreMocks: true,

  // Verbose output
  verbose: true,
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig);
