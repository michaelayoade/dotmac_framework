/** @type {import('jest').Config} */
const config = {
  displayName: '@dotmac/monitoring',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: [
    '<rootDir>/__tests__/setup.ts'
  ],
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.{test,spec}.{js,jsx,ts,tsx}'
  ],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/index.{js,jsx,ts,tsx}'
  ],
  coverageReporters: [
    'text',
    'lcov',
    'html'
  ],
  coverageDirectory: 'coverage',
  coverageThreshold: {
    global: {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85
    }
  },
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', {
      presets: [
        ['@babel/preset-env', { targets: { node: 'current' } }],
        ['@babel/preset-react', { runtime: 'automatic' }],
        '@babel/preset-typescript'
      ]
    }]
  },
  moduleFileExtensions: [
    'js',
    'jsx',
    'ts',
    'tsx',
    'json',
    'node'
  ],
  testTimeout: 10000,
  verbose: true,
  // Additional config for monitoring tests
  globals: {
    'process.env': {
      NODE_ENV: 'test',
      SENTRY_DSN: 'mock-sentry-dsn',
      MONITORING_ENABLED: 'true'
    }
  },
  // Mock external monitoring services
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    // Mock Sentry SDK for consistent testing
    '^@sentry/react$': '<rootDir>/__tests__/mocks/sentry-react.js',
    '^@sentry/tracing$': '<rootDir>/__tests__/mocks/sentry-tracing.js',
    // Mock performance monitoring libraries
    '^web-vitals$': '<rootDir>/__tests__/mocks/web-vitals.js'
  }
};

module.exports = config;
