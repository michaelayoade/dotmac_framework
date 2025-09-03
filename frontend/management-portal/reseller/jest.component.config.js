const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

// Component test configuration - focused on React component testing
const componentJestConfig = {
  displayName: 'Component Tests',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js', '<rootDir>/tests/setup/component-setup.js'],
  testEnvironment: 'jest-environment-jsdom',

  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/(.*)$': '<rootDir>/../../../packages/$1',
    // Mock CSS modules
    '\\.module\\.(css|sass|scss)$': 'identity-obj-proxy',
    '\\.css$': 'identity-obj-proxy',
  },

  // Only run component tests
  testMatch: [
    '<rootDir>/src/components/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/components/**/*.{test,spec}.{js,jsx,ts,tsx}',
    '<rootDir>/tests/components/**/*.{test,spec}.{js,jsx,ts,tsx}',
  ],

  // Exclude other test types
  testPathIgnorePatterns: [
    '<rootDir>/.next/',
    '<rootDir>/node_modules/',
    '<rootDir>/tests/e2e/',
    '<rootDir>/tests/integration/',
    '<rootDir>/tests/unit/',
    '.*\\.unit\\..*',
    '.*\\.integration\\..*',
    '.*\\.e2e\\..*',
  ],

  collectCoverageFrom: [
    'src/components/**/*.{js,jsx,ts,tsx}',
    'src/hooks/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/index.{js,jsx,ts,tsx}',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/*.unit.*',
    '!src/**/*.integration.*',
    '!src/**/*.e2e.*',
  ],

  coverageReporters: ['text', 'lcov', 'json-summary'],
  coverageDirectory: 'coverage/components',

  // Coverage thresholds specifically for components
  coverageThreshold: {
    global: {
      branches: 75,
      functions: 75,
      lines: 75,
      statements: 75,
    },
    'src/components/**/*.{js,jsx,ts,tsx}': {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },

  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.mjs$|@dotmac/.*|@testing-library/.*|recharts|react-window|react-error-boundary))',
  ],

  extensionsToTreatAsEsm: ['.ts', '.tsx'],

  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }],
  },

  moduleDirectories: ['node_modules', '<rootDir>/src'],
  setupFiles: ['<rootDir>/jest.env.js'],

  // Standard timeout for component tests
  testTimeout: 15000,

  clearMocks: true,
  restoreMocks: true,
  verbose: true,

  // Component test specific options
  testEnvironmentOptions: {
    url: 'http://localhost:3004',
  },

  // Snapshot serializer for better component snapshots
  snapshotSerializers: ['@emotion/jest/serializer'],

  // React Testing Library configuration
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/(.*)$': '<rootDir>/../../../packages/$1',
    '\\.module\\.(css|sass|scss)$': 'identity-obj-proxy',
    '\\.css$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/tests/__mocks__/fileMock.js',
  },

  // Enhanced error reporting for component tests
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: 'test-results',
        outputName: 'component-results.xml',
        suiteName: 'Component Tests',
      },
    ],
  ],
};

module.exports = createJestConfig(componentJestConfig);
