module.exports = {
  displayName: '@dotmac/tenancy',
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.(ts|tsx)$': '@swc/jest',
  },
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/headless/api$': '<rootDir>/src/__mocks__/api.ts',
    '^@dotmac/primitives/(.*)$': '<rootDir>/../primitives/src/$1',
    '^@dotmac/providers/(.*)$': '<rootDir>/../providers/src/$1',
  },
  setupFilesAfterEnv: ['<rootDir>/src/__tests__/setup.ts'],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.tsx',
    '!src/index.ts',
    '!src/__tests__/**',
    '!src/__mocks__/**',
  ],
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{ts,tsx}',
    '<rootDir>/src/**/*.{test,spec}.{ts,tsx}',
  ],
  testPathIgnorePatterns: ['<rootDir>/src/__tests__/setup.ts'],
};
