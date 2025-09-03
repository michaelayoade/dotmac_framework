/**
 * Unified Jest Configuration for DotMac Platform
 * Eliminates duplication and standardizes testing across all apps
 */

const path = require('path');

// Environment detection
const isCI = process.env.CI === 'true';
const isDev = process.env.NODE_ENV === 'development';

/**
 * Create unified Jest config for any portal/package
 */
function createUnifiedJestConfig(options = {}) {
  const {
    displayName = 'DotMac Tests',
    testEnvironment = 'jsdom',
    setupFiles = [],
    coverageThreshold = {
      global: {
        statements: 80,
        branches: 75,
        functions: 80,
        lines: 80,
      },
    },
    moduleNameMapper = {},
    testMatch = [
      '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
      '<rootDir>/src/**/*.{test,spec}.{js,jsx,ts,tsx}',
    ],
  } = options;

  return {
    displayName,
    testEnvironment,

    // Unified setup files
    setupFilesAfterEnv: ['<rootDir>/../../testing/setup/jest.setup.ts', ...setupFiles],

    // Standardized module mapping
    moduleNameMapper: {
      // Shared packages (DRY imports) - specific paths first
      '^@dotmac/([^/]+)/(.+)$': '<rootDir>/../../packages/$1/src/$2',
      '^@dotmac/(.*)$': '<rootDir>/../../packages/$1/src',
      '^@test/(.*)$': '<rootDir>/../../testing/$1',

      // Common aliases
      '^@/(.*)$': '<rootDir>/src/$1',
      '^~/(.*)$': '<rootDir>/src/$1',

      // Next.js mocks
      '^next/navigation$': '<rootDir>/../../testing/mocks/nextjs.js',
      '^next/image$': '<rootDir>/../../testing/mocks/nextjs.js',
      '^next/link$': '<rootDir>/../../testing/mocks/nextjs.js',

      // Asset mocks
      '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
      '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/../../testing/mocks/fileMock.js',

      // Custom overrides
      ...moduleNameMapper,
    },

    // Test patterns
    testMatch,

    // Ignore patterns
    testPathIgnorePatterns: [
      '<rootDir>/.next/',
      '<rootDir>/dist/',
      '<rootDir>/build/',
      '<rootDir>/node_modules/',
    ],

    // Coverage configuration
    collectCoverageFrom: [
      'src/**/*.{js,jsx,ts,tsx}',
      '!src/**/*.d.ts',
      '!src/**/__tests__/**',
      '!src/**/__mocks__/**',
      '!src/**/*.stories.{js,jsx,ts,tsx}',
      '!src/**/index.{js,jsx,ts,tsx}',
    ],

    coverageThreshold,
    coverageDirectory: '<rootDir>/coverage',
    coverageReporters: ['text', 'lcov', 'html', 'json-summary'],

    // Transform configuration (SWC for speed)
    transform: {
      '^.+\\.(js|jsx|ts|tsx)$': [
        '@swc/jest',
        {
          jsc: {
            transform: {
              react: {
                runtime: 'automatic',
              },
            },
            parser: {
              syntax: 'typescript',
              tsx: true,
              decorators: true,
            },
          },
        },
      ],
    },

    // Module file extensions
    moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],

    // Performance optimization
    maxWorkers: isCI ? 1 : '50%',
    cache: true,
    cacheDirectory: '<rootDir>/node_modules/.cache/jest',

    // Timeouts
    testTimeout: 10000,

    // Transform ignore patterns
    transformIgnorePatterns: ['node_modules/(?!(msw|@faker-js/faker|@dotmac|@mswjs)/)'],

    // Watch mode configuration
    watchPlugins: ['jest-watch-typeahead/filename', 'jest-watch-typeahead/testname'],

    // Test environment options
    testEnvironmentOptions: {
      url: 'http://localhost:3000',
    },

    // Clear mocks between tests
    clearMocks: true,
    restoreMocks: true,

    // Verbose output
    verbose: !isCI,
  };
}

// Specific configurations for different portal types
const portalConfigs = {
  customer: () =>
    createUnifiedJestConfig({
      displayName: 'Customer Portal Tests',
      testEnvironmentOptions: {
        url: 'http://localhost:3001',
      },
      coverageThreshold: {
        global: {
          statements: 90,
          branches: 85,
          functions: 90,
          lines: 90,
        },
      },
    }),

  admin: () =>
    createUnifiedJestConfig({
      displayName: 'Admin Portal Tests',
      testEnvironmentOptions: {
        url: 'http://localhost:3000',
      },
      coverageThreshold: {
        global: {
          statements: 85,
          branches: 80,
          functions: 85,
          lines: 85,
        },
      },
    }),

  technician: () =>
    createUnifiedJestConfig({
      displayName: 'Technician Portal Tests',
      testEnvironmentOptions: {
        url: 'http://localhost:3002',
      },
      setupFiles: ['<rootDir>/jest-pwa-setup.js'],
      coverageThreshold: {
        global: {
          statements: 80,
          branches: 75,
          functions: 80,
          lines: 80,
        },
      },
    }),

  package: (packageName) =>
    createUnifiedJestConfig({
      displayName: `${packageName} Package Tests`,
      testEnvironment: 'node',
      coverageThreshold: {
        global: {
          statements: 95,
          branches: 90,
          functions: 95,
          lines: 95,
        },
      },
    }),
};

module.exports = {
  createUnifiedJestConfig,
  portalConfigs,
};
