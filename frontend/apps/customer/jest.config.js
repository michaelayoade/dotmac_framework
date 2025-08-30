/**
 * DRY Jest configuration for Customer Portal - extends shared base config
 */

// Import our DRY base configuration
const baseConfig = require('../../testing/jest.config.base.js');

/** @type {import('jest').Config} */
module.exports = {
  ...baseConfig,
  displayName: 'Customer App Tests',

  // Setup files - DRY setup first, then app-specific
  setupFilesAfterEnv: [
    '<rootDir>/../../testing/setup/jest.setup.ts',
    '<rootDir>/jest-setup.js'
  ],

  // Next.js specific ignore patterns
  testPathIgnorePatterns: ['<rootDir>/.next/', '<rootDir>/node_modules/'],

  // Customer-specific coverage (extends base config)
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

  // Merge DRY module mappings with app-specific ones
  moduleNameMapper: {
    ...baseConfig.moduleNameMapper,

    // App-specific aliases
    '^@/(.*)$': '<rootDir>/src/$1',
    '^~/(.*)$': '<rootDir>/src/$1',

    // Override base for local package resolution
    '^@dotmac/(.*)$': '<rootDir>/../../packages/$1/src',
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
};
