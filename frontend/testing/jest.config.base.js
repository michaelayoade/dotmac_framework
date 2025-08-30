/**
 * Base Jest configuration following DRY principles.
 * Shared across all frontend applications.
 */

module.exports = {
  // Test environment
  testEnvironment: 'jsdom',

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/testing/setup/jest.setup.ts'],

  // Module name mapping (DRY path resolution)
  moduleNameMapper: {
    // Shared packages
    '@dotmac/headless': '<rootDir>/packages/headless/src',
    '@dotmac/primitives': '<rootDir>/packages/primitives/src',
    '@dotmac/styled-components': '<rootDir>/packages/styled-components/src',
    '@dotmac/monitoring': '<rootDir>/packages/monitoring/src',

    // Test utilities (DRY testing infrastructure)
    '@test/utils': '<rootDir>/testing/utils',
    '@test/fixtures': '<rootDir>/testing/fixtures',
    '@test/mocks': '<rootDir>/testing/mocks',
    '@test/factories': '<rootDir>/testing/factories',

    // CSS/Asset mocks
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/testing/mocks/fileMock.js'
  },

  // Test patterns (consistent across all apps)
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.{test,spec}.{js,jsx,ts,tsx}',
    '<rootDir>/tests/**/*.{test,spec}.{js,jsx,ts,tsx}'
  ],

  // Coverage configuration (DRY coverage standards)
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/__tests__/**',
    '!src/**/index.{js,jsx,ts,tsx}'
  ],

  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70
    }
  },

  // Transform configuration
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['@swc/jest', {
      jsc: {
        transform: {
          react: {
            runtime: 'automatic'
          }
        }
      }
    }]
  },

  // Module file extensions
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],

  // Test timeout
  testTimeout: 10000,

  // Watch mode configuration
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname'
  ],

  // Transform ignore patterns - allow transforming faker
  transformIgnorePatterns: [
    'node_modules/(?!(@faker-js/faker)/)'
  ],

  // Performance optimization
  maxWorkers: '50%',
  cache: true,
  cacheDirectory: '<rootDir>/node_modules/.cache/jest'
};
