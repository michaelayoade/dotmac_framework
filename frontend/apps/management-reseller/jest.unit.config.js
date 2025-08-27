const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

// Unit test configuration - focused on isolated testing
const unitJestConfig = {
  displayName: 'Unit Tests',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/(.*)$': '<rootDir>/../../../packages/$1',
  },
  
  // Only run unit tests (exclude integration and e2e)
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.unit.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.unit.{test,spec}.{js,jsx,ts,tsx}',
    '<rootDir>/tests/unit/**/*.{test,spec}.{js,jsx,ts,tsx}',
  ],
  
  // Exclude integration and e2e tests
  testPathIgnorePatterns: [
    '<rootDir>/.next/',
    '<rootDir>/node_modules/',
    '<rootDir>/tests/e2e/',
    '<rootDir>/tests/integration/',
    '.*\\.integration\\..*',
    '.*\\.e2e\\..*',
  ],
  
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/index.{js,jsx,ts,tsx}',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/app/**', // Exclude Next.js app directory
    '!src/middleware.ts',
    '!src/**/*.integration.*',
    '!src/**/*.e2e.*',
  ],
  
  coverageReporters: ['text', 'lcov', 'json-summary'],
  coverageDirectory: 'coverage/unit',
  
  // Higher coverage thresholds for unit tests
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
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
  
  // Shorter timeout for unit tests
  testTimeout: 10000,
  
  clearMocks: true,
  restoreMocks: true,
  verbose: false, // Less verbose for unit tests
  
  // Mock external dependencies more aggressively for unit tests
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/(.*)$': '<rootDir>/../../../packages/$1',
    // Mock API calls for unit tests
    '^@/lib/api/(.*)$': '<rootDir>/src/__mocks__/api/$1',
  },
}

module.exports = createJestConfig(unitJestConfig)