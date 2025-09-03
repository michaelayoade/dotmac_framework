/**
 * DRY Jest configuration for Technician Mobile App - extends shared base config
 * Specialized for mobile testing with memory optimizations
 */

const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

// Import our DRY base configuration
const baseConfig = require('../../testing/jest.config.base.js');

const customJestConfig = {
  ...baseConfig,
  displayName: 'Technician Mobile App',

  // Mobile-specific setup files
  setupFiles: ['<rootDir>/src/__tests__/setup/global-setup.ts'],
  setupFilesAfterEnv: ['<rootDir>/../../testing/setup/jest.setup.ts', '<rootDir>/jest.setup.js'],

  testPathIgnorePatterns: ['<rootDir>/.next/', '<rootDir>/node_modules/', '<rootDir>/cypress/'],

  // Mobile-optimized coverage with granular thresholds
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/index.{js,jsx,ts,tsx}',
    '!src/__tests__/**',
    '!src/**/__tests__/**',
    '!src/**/*.test.{js,jsx,ts,tsx}',
    '!src/**/*.spec.{js,jsx,ts,tsx}',
  ],

  coverageThreshold: {
    global: {
      branches: 75,
      functions: 80,
      lines: 80,
      statements: 80,
    },
    './src/lib/': {
      branches: 85,
      functions: 90,
      lines: 90,
      statements: 90,
    },
    './src/components/': {
      branches: 70,
      functions: 75,
      lines: 75,
      statements: 75,
    },
  },

  // Merge DRY module mappings with mobile-specific ones
  moduleNameMapper: {
    ...baseConfig.moduleNameMapper,

    // App-specific aliases
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@/components/(.*)$': '<rootDir>/src/components/$1',
    '^@/lib/(.*)$': '<rootDir>/src/lib/$1',
    '^@/hooks/(.*)$': '<rootDir>/src/hooks/$1',

    // DRY package aliases
    '^@dotmac/(.*)$': '<rootDir>/../../packages/$1/src',

    // Mobile-specific mocks
    'lucide-react': 'identity-obj-proxy',
    'framer-motion': 'identity-obj-proxy',
    'framer-motion/dist/es/motion': 'identity-obj-proxy',
    '^dexie$': '<rootDir>/src/__tests__/mocks/dexie.js',
  },

  moduleDirectories: ['node_modules', '<rootDir>/'],

  testEnvironmentOptions: {
    url: 'http://localhost:3003',
  },

  globals: {
    'ts-jest': {
      tsconfig: 'tsconfig.json',
    },
  },

  testTimeout: 15000,

  // Mobile memory optimizations
  maxWorkers: 1,
  clearMocks: true,
  restoreMocks: true,
  resetMocks: true,
  workerIdleMemoryLimit: '512MB',
  logHeapUsage: true,
  detectLeaks: false,

  // Optimize module handling for mobile libraries
  transformIgnorePatterns: [
    'node_modules/(?!(framer-motion|lucide-react)/)',
    '^.+\\.module\\.(css|sass|scss)$',
  ],
};

module.exports = createJestConfig(customJestConfig);
