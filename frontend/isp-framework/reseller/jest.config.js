/**
 * DRY Jest configuration for Reseller Portal - extends shared base config
 * Maintains Next.js compatibility while using our DRY testing architecture
 */

const nextJest = require('next/jest');

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: './',
});

// Import our DRY base configuration
const baseConfig = require('../../testing/jest.config.base.js');

// Merge DRY base config with Next.js specific config
const customJestConfig = {
  ...baseConfig,
  displayName: 'Reseller Portal',

  // Next.js specific setup
  setupFilesAfterEnv: [
    '<rootDir>/../../testing/setup/jest.setup.ts', // DRY setup first
    '<rootDir>/jest.setup.js', // Then app-specific setup
  ],

  testPathIgnorePatterns: ['<rootDir>/.next/', '<rootDir>/node_modules/'],

  // Reseller-specific coverage (extends base config)
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/index.{js,jsx,ts,tsx}',
    '!src/app/page.tsx', // Exclude simple pages
    '!src/app/layout.tsx',
    '!src/middleware.ts',
    '!src/instrumentation.ts',
  ],

  coverageDirectory: 'coverage',

  // Merge DRY module mappings with app-specific ones
  moduleNameMapper: {
    ...baseConfig.moduleNameMapper,

    // App-specific aliases
    '^@/(.*)$': '<rootDir>/src/$1',

    // DRY package aliases (override base for local resolution)
    '^@dotmac/(.*)$': '<rootDir>/../../packages/$1/src',

    // Next.js specific mappings
    '\\.module\\.(css|sass|scss)$': 'identity-obj-proxy',
  },

  // Axe accessibility testing configuration
  testTimeout: 30000,

  transformIgnorePatterns: ['/node_modules/', '^.+\\.module\\.(css|sass|scss)$'],
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig);
