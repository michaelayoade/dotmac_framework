/**
 * Enhanced Jest Configuration for Reseller Portal
 * 
 * Provides comprehensive testing setup with coverage requirements,
 * performance testing, accessibility testing, and integration testing support.
 */

const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js', '<rootDir>/tests/setup/enhanced-setup.js'],
  testEnvironment: 'jsdom',
  
  // Test file patterns - comprehensive coverage
  testMatch: [
    '**/__tests__/**/*.(js|jsx|ts|tsx)',
    '**/?(*.)+(spec|test).(js|jsx|ts|tsx)',
    '**/tests/**/*.(js|jsx|ts|tsx)',
  ],

  // Module name mapping for absolute imports and packages
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/testing$': '<rootDir>/../../packages/testing/src/index.ts',
    '^@dotmac/headless$': '<rootDir>/../../packages/headless/src/index.ts',
    '^@dotmac/primitives$': '<rootDir>/../../packages/primitives/src/index.ts',
    '^@dotmac/security$': '<rootDir>/../../packages/security/src/index.ts',
    '^@dotmac/styled-components$': '<rootDir>/../../packages/styled-components/src/index.ts',
  },

  // Transform configuration
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }],
    '^.+\\.css$': 'jest-transform-css',
    '^.+\\.(jpg|jpeg|png|gif|svg)$': 'jest-transform-file',
  },

  // Transform ignore patterns - allow testing of modern modules
  transformIgnorePatterns: [
    'node_modules/(?!(@dotmac|@tanstack|framer-motion|recharts|leaflet)/)',
  ],

  // Coverage configuration - enforce 80% minimum
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/index.{js,jsx,ts,tsx}',
    '!src/**/*.test.{js,jsx,ts,tsx}',
    '!src/**/*.spec.{js,jsx,ts,tsx}',
    '!src/app/layout.tsx',
    '!src/app/page.tsx',
    '!src/app/globals.css',
  ],

  // Coverage thresholds - enforce quality gates
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
    // Specific thresholds for critical components
    './src/components/territory/': {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85,
    },
    './src/components/customers/': {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85,
    },
    './src/middleware.ts': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90,
    },
  },

  // Coverage reporters
  coverageReporters: [
    'text',
    'lcov',
    'html',
    'json-summary',
    'clover',
  ],
  coverageDirectory: 'coverage',

  // Test path ignore patterns
  testPathIgnorePatterns: [
    '<rootDir>/.next/',
    '<rootDir>/node_modules/',
    '<rootDir>/coverage/',
    '<rootDir>/dist/',
  ],

  // Module file extensions
  moduleFileExtensions: ['js', 'jsx', 'ts', 'tsx', 'json', 'css'],

  // Global setup and teardown
  globalSetup: '<rootDir>/tests/setup/global-setup.js',
  globalTeardown: '<rootDir>/tests/setup/global-teardown.js',

  // Test timeout for complex integration tests
  testTimeout: 30000,

  // Verbose output for CI/CD
  verbose: process.env.CI === 'true',

  // Fail fast in CI
  bail: process.env.CI === 'true' ? 1 : 0,

  // Max workers for parallel execution
  maxWorkers: process.env.CI ? 2 : '50%',

  // Cache configuration
  cache: true,
  cacheDirectory: '<rootDir>/.jest-cache',

  // Reporter configuration
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: 'test-results',
        outputName: 'junit.xml',
        ancestorSeparator: ' › ',
        uniqueOutputName: 'false',
        suiteNameTemplate: '{filepath}',
        classNameTemplate: '{classname}',
        titleTemplate: '{title}',
      },
    ],
    [
      'jest-html-reporters',
      {
        publicDir: './test-results',
        filename: 'report.html',
        expand: true,
        hideIcon: false,
        pageTitle: 'Reseller Portal Test Report',
      },
    ],
  ],

  // Watch mode configuration
  watchPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/.next/',
    '<rootDir>/coverage/',
    '<rootDir>/test-results/',
  ],

  // Error handling
  errorOnDeprecated: true,

  // Snapshot configuration
  updateSnapshot: process.env.CI !== 'true',

  // Clear mocks between tests
  clearMocks: true,
  restoreMocks: true,

  // Mock configuration
  haste: {
    throwOnModuleCollision: false,
  },

  // Custom test environment options
  testEnvironmentOptions: {
    url: 'http://localhost:3000',
    userAgent: 'node.js',
  },

  // Project configuration for multi-project setup
  projects: [
    {
      displayName: 'unit',
      testMatch: [
        '<rootDir>/src/**/__tests__/**/*.(js|jsx|ts|tsx)',
        '<rootDir>/src/**/*.(test|spec).(js|jsx|ts|tsx)',
      ],
      testEnvironment: 'jsdom',
    },
    {
      displayName: 'integration',
      testMatch: ['<rootDir>/tests/integration/**/*.(js|jsx|ts|tsx)'],
      testEnvironment: 'jsdom',
      setupFilesAfterEnv: [
        '<rootDir>/jest.setup.js',
        '<rootDir>/tests/setup/integration-setup.js',
      ],
    },
    {
      displayName: 'e2e',
      testMatch: ['<rootDir>/tests/e2e/**/*.(js|jsx|ts|tsx)'],
      testEnvironment: 'node',
      setupFilesAfterEnv: ['<rootDir>/tests/setup/e2e-setup.js'],
    },
  ],
};

module.exports = createJestConfig(customJestConfig);