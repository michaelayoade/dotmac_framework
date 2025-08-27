/** @type {import('jest').Config} */
module.exports = {
  displayName: 'Customer App Tests',
  testEnvironment: 'jsdom',

  // Test file patterns
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.test.[jt]s?(x)',
    '<rootDir>/src/**/*.test.[jt]s?(x)',
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    '/dist/',
    '.*\\.e2e\\.test\\.[jt]sx?$',
  ],

  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/jest-setup.js'
  ],

  // Transform configuration
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': [
      '@swc/jest',
      {
        jsc: {
          parser: {
            syntax: 'typescript',
            tsx: true,
            decorators: true,
          },
          transform: {
            react: {
              runtime: 'automatic',
            },
          },
        },
      },
    ],
  },

  // Module name mapping
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^~/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/headless$': '<rootDir>/../../packages/headless/src',
    '^@dotmac/headless/(.*)$': '<rootDir>/../../packages/headless/src/$1',
    '^@dotmac/primitives$': '<rootDir>/../../packages/primitives/src',
    '^@dotmac/primitives/(.*)$': '<rootDir>/../../packages/primitives/src/$1',
    '^@dotmac/styled-components$': '<rootDir>/../../packages/styled-components/src',
    '^@dotmac/styled-components/(.*)$': '<rootDir>/../../packages/styled-components/src/$1',
    '^@dotmac/mapping$': '<rootDir>/../../packages/mapping/src',
    '^@dotmac/mapping/(.*)$': '<rootDir>/../../packages/mapping/src/$1',
    '^@dotmac/testing$': '<rootDir>/../../packages/testing/src',
    '^@dotmac/testing/(.*)$': '<rootDir>/../../packages/testing/src/$1',
    '\\.(css|less|scss)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|svg)$': '<rootDir>/__mocks__/fileMock.js',
  },

  // Coverage configuration
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/__tests__/**',
    '!src/**/__mocks__/**',
    '!src/**/*.stories.*',
    '!src/app/**/layout.tsx',
    '!src/app/**/loading.tsx',
    '!src/app/**/error.tsx',
    '!src/app/**/not-found.tsx',
    '!src/app/globals.css',
  ],
  
  // High coverage thresholds for Phase 2
  coverageThreshold: {
    global: {
      statements: 90,
      branches: 85,
      functions: 90,
      lines: 90,
    },
  },

  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['text', 'lcov', 'html', 'json-summary'],

  // Test environment options
  testEnvironmentOptions: {
    url: 'http://localhost:3001',
  },

  // Clear mocks between tests
  clearMocks: true,
  restoreMocks: true,

  // Verbose output for better debugging
  verbose: true,

  // Performance
  maxWorkers: '50%',
};