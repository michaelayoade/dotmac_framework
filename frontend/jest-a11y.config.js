/** @type {import('jest').Config} */
module.exports = {
  displayName: 'Accessibility Tests',
  testMatch: ['**/__tests__/**/*.(a11y|accessibility).(test|spec).[jt]s?(x)'],
  setupFilesAfterEnv: ['<rootDir>/jest-a11y-setup.js'],
  testEnvironment: 'jsdom',
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@dotmac/(.*)$': '<rootDir>/packages/$1',
  },
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['@swc/jest'],
  },
  collectCoverageFrom: [
    'packages/**/*.{ts,tsx}',
    'apps/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
  ],
  coverageThreshold: {
    global: {
      statements: 80,
      branches: 80,
      functions: 80,
      lines: 80,
    },
  },
};
