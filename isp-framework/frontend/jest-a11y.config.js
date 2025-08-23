/** @type {import('jest').Config} */
module.exports = {
  displayName: 'Accessibility Tests',
  testMatch: ['**/__tests__/**/*.(a11y|accessibility).(test|spec).[jt]s?(x)'],
  setupFilesAfterEnv: ['<rootDir>/jest-a11y-setup.js'],
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '^@dotmac/headless$': '<rootDir>/packages/headless/src',
    '^@dotmac/headless/(.*)$': '<rootDir>/packages/headless/src/$1',
    '^@dotmac/primitives$': '<rootDir>/packages/primitives/src',
    '^@dotmac/primitives/(.*)$': '<rootDir>/packages/primitives/src/$1',
    '^@dotmac/styled-components$': '<rootDir>/packages/styled-components/src',
    '^@dotmac/styled-components/(.*)$': '<rootDir>/packages/styled-components/src/$1',
    '^~/(.*)$': '<rootDir>/$1',
    '\\.(css|less|scss)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|svg)$': '<rootDir>/__mocks__/fileMock.js',
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
