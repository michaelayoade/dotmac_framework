const path = require('path');

/** @type {import('jest').Config} */
module.exports = {
  displayName: 'Integration Tests',
  testEnvironment: 'jsdom',
  
  // Test file patterns
  testMatch: [
    '<rootDir>/**/*.test.{ts,tsx}',
  ],
  
  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/setup.ts'
  ],
  
  // Module name mapping
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/../../src/$1',
    '^@/tests/(.*)$': '<rootDir>/../$1'
  },
  
  // TypeScript support
  preset: 'ts-jest',
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: '<rootDir>/../../tsconfig.json'
    }]
  },
  
  // Coverage collection
  collectCoverageFrom: [
    '<rootDir>/../../src/lib/**/*.{ts,tsx}',
    '<rootDir>/../../src/components/**/*.{ts,tsx}',
    '!<rootDir>/../../src/**/*.d.ts',
    '!<rootDir>/../../src/**/*.stories.{ts,tsx}',
    '!<rootDir>/../../src/**/index.{ts,tsx}'
  ],
  
  // Coverage thresholds for integration tests
  coverageThreshold: {
    global: {
      branches: 60,
      functions: 60,
      lines: 60,
      statements: 60
    }
  },
  
  // Test timeout (longer for integration tests)
  testTimeout: 30000,
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '<rootDir>/.next/',
    '<rootDir>/node_modules/',
    '<rootDir>/tests/e2e/',
    '<rootDir>/tests/unit/'
  ],
  
  // Module resolution
  moduleDirectories: ['node_modules', '<rootDir>/'],
  
  // Clear mocks between tests
  clearMocks: true,
  restoreMocks: true,
  
  // Verbose output for integration tests
  verbose: true,
  
  // Globals
  globals: {
    'ts-jest': {
      isolatedModules: true
    }
  },
  
  // Transform ignore patterns
  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.(mjs|esm)$))'
  ],
  
  // Add JSX support
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json']
};