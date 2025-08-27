/**
 * Jest Configuration for Tenant Portal
 * Simplified testing setup
 */

const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const customJestConfig = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/__tests__/setup.ts'],
  
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{test,spec}.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.{test,spec}.{js,jsx,ts,tsx}',
  ],
  
  testPathIgnorePatterns: [
    '<rootDir>/.next/',
    '<rootDir>/node_modules/',
    '<rootDir>/src/__tests__/setup.ts',
    '<rootDir>/src/__tests__/env-setup.ts',
    '<rootDir>/src/__tests__/global-setup.ts',
    '<rootDir>/src/__tests__/global-teardown.ts',
    '<rootDir>/src/__tests__/e2e/global-setup.ts',
    '<rootDir>/src/__tests__/e2e/global-teardown.ts',
    '<rootDir>/src/__tests__/mocks/',
  ],
  
  collectCoverage: false,
  testTimeout: 10000,
  verbose: true,
};

module.exports = createJestConfig(customJestConfig);