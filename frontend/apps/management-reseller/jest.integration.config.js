const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

// Integration test configuration - tests component integration and API interactions
const integrationJestConfig = {
  displayName: 'Integration Tests',
  setupFilesAfterEnv: [
    '<rootDir>/jest.setup.js',
    '<rootDir>/tests/setup/integration-setup.js'
  ],
  testEnvironment: 'jest-environment-jsdom',
  
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/(.*)$': '<rootDir>/../../../packages/$1',
  },
  
  // Only run integration tests
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.integration.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.integration.{test,spec}.{js,jsx,ts,tsx}',
    '<rootDir>/tests/integration/**/*.{test,spec}.{js,jsx,ts,tsx}',
  ],
  
  // Exclude unit and e2e tests
  testPathIgnorePatterns: [
    '<rootDir>/.next/',
    '<rootDir>/node_modules/',
    '<rootDir>/tests/e2e/',
    '.*\\.unit\\..*',
    '.*\\.e2e\\..*',
  ],
  
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/index.{js,jsx,ts,tsx}',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/app/**',
    '!src/middleware.ts',
    '!src/**/*.unit.*',
    '!src/**/*.e2e.*',
  ],
  
  coverageReporters: ['text', 'lcov', 'json-summary'],
  coverageDirectory: 'coverage/integration',
  
  // Lower coverage thresholds for integration tests (focus on critical paths)
  coverageThreshold: {
    global: {
      branches: 60,
      functions: 60,
      lines: 60,
      statements: 60,
    },
  },
  
  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.mjs$|@dotmac/.*|recharts|react-window|react-error-boundary))',
  ],
  
  extensionsToTreatAsEsm: ['.ts', '.tsx'],
  
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }],
  },
  
  moduleDirectories: ['node_modules', '<rootDir>/src'],
  setupFiles: ['<rootDir>/jest.env.js'],
  
  // Longer timeout for integration tests
  testTimeout: 30000,
  
  clearMocks: true,
  restoreMocks: true,
  verbose: true,
  
  // Test environment variables for integration tests
  testEnvironmentOptions: {
    url: 'http://localhost:3004',
  },
  
  // Integration test specific globals
  globals: {
    'process.env.NODE_ENV': 'test',
    'process.env.NEXT_PUBLIC_MANAGEMENT_API_URL': 'http://localhost:8000',
  },
  
  // Allow real HTTP requests in integration tests (with MSW mocking)
  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.mjs$|@dotmac/.*|msw|@mswjs/.*|recharts|react-window|react-error-boundary))',
  ],
}

module.exports = createJestConfig(integrationJestConfig)