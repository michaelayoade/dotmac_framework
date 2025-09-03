/** @type {import('jest').Config} */
module.exports = {
  displayName: 'DotMac Frontend Tests',

  // Projects for different test types
  projects: [
    // Unit Tests
    {
      displayName: 'Unit Tests',
      roots: ['<rootDir>/packages', '<rootDir>/tests'],
      testMatch: ['<rootDir>/**/__tests__/**/*.test.[jt]s?(x)', '<rootDir>/**/*.test.[jt]s?(x)'],
      testPathIgnorePatterns: [
        '/node_modules/',
        '.*\\.e2e\\.test\\.[jt]sx?$',
        '.*\\.integration\\.test\\.[jt]sx?$',
        '.*\\.a11y\\.test\\.[jt]sx?$',
        '.*\\.visual\\.test\\.[jt]sx?$',
        '<rootDir>/tests/e2e/',
        '<rootDir>/tests/visual/',
        '<rootDir>/tests/integration/',
        '<rootDir>/tests/a11y/',
        '<rootDir>/apps/',
      ],
      modulePathIgnorePatterns: ['<rootDir>/apps/.*/__mocks__/'],
      setupFilesAfterEnv: ['<rootDir>/jest-setup.js'],
      testEnvironment: 'jsdom',
      transform: {
        '^.+\\.(js|jsx|ts|tsx)$': [
          '@swc/jest',
          {
            jsc: {
              parser: {
                syntax: 'typescript',
                tsx: true,
                decorators: true,
              },
              transform: {
                react: {
                  runtime: 'automatic',
                },
              },
            },
          },
        ],
      },
      moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/$1',
        '^@dotmac/headless$': '<rootDir>/packages/headless/src',
        '^@dotmac/headless/(.*)$': '<rootDir>/packages/headless/src/$1',
        '^@dotmac/primitives$': '<rootDir>/packages/primitives/src',
        '^@dotmac/primitives/(.*)$': '<rootDir>/packages/primitives/src/$1',
        '^@dotmac/styled-components$': '<rootDir>/packages/styled-components/src',
        '^@dotmac/styled-components/(.*)$': '<rootDir>/packages/styled-components/src/$1',
        '^@dotmac/registry$': '<rootDir>/packages/registry/src',
        '^@dotmac/registry/(.*)$': '<rootDir>/packages/registry/src/$1',
        '^@dotmac/mapping$': '<rootDir>/packages/mapping/src',
        '^@dotmac/mapping/(.*)$': '<rootDir>/packages/mapping/src/$1',
        '^@dotmac/security$': '<rootDir>/packages/security/src',
        '^@dotmac/security/(.*)$': '<rootDir>/packages/security/src/$1',
        '^@dotmac/testing$': '<rootDir>/packages/testing/src',
        '^@dotmac/testing/(.*)$': '<rootDir>/packages/testing/src/$1',
        '^@dotmac/monitoring$': '<rootDir>/packages/monitoring/src',
        '^@dotmac/monitoring/(.*)$': '<rootDir>/packages/monitoring/src/$1',
        '^@dotmac/patterns$': '<rootDir>/packages/patterns/src',
        '^@dotmac/patterns/(.*)$': '<rootDir>/packages/patterns/src/$1',
        '^~/(.*)$': '<rootDir>/$1',
        '\\.(css|less|scss)$': 'identity-obj-proxy',
        '\\.(jpg|jpeg|png|gif|svg)$': '<rootDir>/__mocks__/fileMock.js',
      },
      collectCoverageFrom: [
        'packages/**/*.{ts,tsx}',
        'apps/**/*.{ts,tsx}',
        '!**/*.d.ts',
        '!**/node_modules/**',
        '!**/.next/**',
        '!**/dist/**',
        '!**/__tests__/**',
        '!**/__mocks__/**',
        '!**/stories/**',
        '!**/*.stories.*',
        '!**/coverage/**',
      ],
      coverageThreshold: {
        global: {
          statements: 85,
          branches: 80,
          functions: 85,
          lines: 85,
        },
      },
    },

    // Integration Tests
    {
      displayName: 'Integration Tests',
      roots: ['<rootDir>/tests'],
      testMatch: ['<rootDir>/**/*.integration.test.[jt]s?(x)'],
      testPathIgnorePatterns: [
        '/node_modules/',
        '<rootDir>/.next/',
        '<rootDir>/dist/',
        '<rootDir>/apps/',
      ],
      modulePathIgnorePatterns: ['<rootDir>/apps/.*/__mocks__/'],
      setupFilesAfterEnv: ['<rootDir>/jest-setup.js', '<rootDir>/jest-integration-setup.js'],
      testEnvironment: 'jsdom',
      transform: {
        '^.+\\.(js|jsx|ts|tsx)$': [
          '@swc/jest',
          {
            jsc: {
              parser: {
                syntax: 'typescript',
                tsx: true,
                decorators: true,
              },
              transform: {
                react: {
                  runtime: 'automatic',
                },
              },
            },
          },
        ],
      },
      moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/$1',
        '^@dotmac/headless$': '<rootDir>/packages/headless/src',
        '^@dotmac/headless/(.*)$': '<rootDir>/packages/headless/src/$1',
        '^@dotmac/primitives$': '<rootDir>/packages/primitives/src',
        '^@dotmac/primitives/(.*)$': '<rootDir>/packages/primitives/src/$1',
        '^@dotmac/styled-components$': '<rootDir>/packages/styled-components/src',
        '^@dotmac/styled-components/(.*)$': '<rootDir>/packages/styled-components/src/$1',
        '^@dotmac/registry$': '<rootDir>/packages/registry/src',
        '^@dotmac/registry/(.*)$': '<rootDir>/packages/registry/src/$1',
        '^@dotmac/mapping$': '<rootDir>/packages/mapping/src',
        '^@dotmac/mapping/(.*)$': '<rootDir>/packages/mapping/src/$1',
        '^@dotmac/security$': '<rootDir>/packages/security/src',
        '^@dotmac/security/(.*)$': '<rootDir>/packages/security/src/$1',
        '^@dotmac/testing$': '<rootDir>/packages/testing/src',
        '^@dotmac/testing/(.*)$': '<rootDir>/packages/testing/src/$1',
        '^@dotmac/monitoring$': '<rootDir>/packages/monitoring/src',
        '^@dotmac/monitoring/(.*)$': '<rootDir>/packages/monitoring/src/$1',
        '^@dotmac/patterns$': '<rootDir>/packages/patterns/src',
        '^@dotmac/patterns/(.*)$': '<rootDir>/packages/patterns/src/$1',
        '^~/(.*)$': '<rootDir>/$1',
        '\\.(css|less|scss)$': 'identity-obj-proxy',
      },
    },

    // Accessibility Tests
    {
      displayName: 'Accessibility Tests',
      roots: ['<rootDir>/tests'],
      testMatch: [
        '<rootDir>/**/__tests__/**/*.a11y.test.[jt]s?(x)',
        '<rootDir>/**/*.accessibility.test.[jt]s?(x)',
        '<rootDir>/tests/a11y/**/*.test.[jt]s?(x)',
      ],
      testPathIgnorePatterns: [
        '/node_modules/',
        '<rootDir>/.next/',
        '<rootDir>/dist/',
        '<rootDir>/apps/',
      ],
      modulePathIgnorePatterns: ['<rootDir>/apps/.*/__mocks__/'],
      setupFilesAfterEnv: ['<rootDir>/jest-a11y-setup.js'],
      testEnvironment: 'jsdom',
      transform: {
        '^.+\\.(js|jsx|ts|tsx)$': [
          '@swc/jest',
          {
            jsc: {
              parser: {
                syntax: 'typescript',
                tsx: true,
                decorators: true,
              },
              transform: {
                react: {
                  runtime: 'automatic',
                },
              },
            },
          },
        ],
      },
      moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/$1',
        '^@dotmac/headless$': '<rootDir>/packages/headless/src',
        '^@dotmac/headless/(.*)$': '<rootDir>/packages/headless/src/$1',
        '^@dotmac/primitives$': '<rootDir>/packages/primitives/src',
        '^@dotmac/primitives/(.*)$': '<rootDir>/packages/primitives/src/$1',
        '^@dotmac/styled-components$': '<rootDir>/packages/styled-components/src',
        '^@dotmac/styled-components/(.*)$': '<rootDir>/packages/styled-components/src/$1',
        '^@dotmac/registry$': '<rootDir>/packages/registry/src',
        '^@dotmac/registry/(.*)$': '<rootDir>/packages/registry/src/$1',
        '^@dotmac/mapping$': '<rootDir>/packages/mapping/src',
        '^@dotmac/mapping/(.*)$': '<rootDir>/packages/mapping/src/$1',
        '^@dotmac/security$': '<rootDir>/packages/security/src',
        '^@dotmac/security/(.*)$': '<rootDir>/packages/security/src/$1',
        '^@dotmac/testing$': '<rootDir>/packages/testing/src',
        '^@dotmac/testing/(.*)$': '<rootDir>/packages/testing/src/$1',
        '^@dotmac/monitoring$': '<rootDir>/packages/monitoring/src',
        '^@dotmac/monitoring/(.*)$': '<rootDir>/packages/monitoring/src/$1',
        '^@dotmac/patterns$': '<rootDir>/packages/patterns/src',
        '^@dotmac/patterns/(.*)$': '<rootDir>/packages/patterns/src/$1',
        '^~/(.*)$': '<rootDir>/$1',
        '\\.(css|less|scss)$': 'identity-obj-proxy',
      },
    },
  ],

  // Global configuration
  collectCoverage: true,
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['text', 'lcov', 'html', 'json-summary'],

  // Test environment options
  testEnvironmentOptions: {
    url: 'http://localhost:3000',
  },

  // Global setup/teardown
  globalSetup: '<rootDir>/jest-global-setup.js',
  globalTeardown: '<rootDir>/jest-global-teardown.js',

  // Watch mode configuration
  watchPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/coverage/',
    '<rootDir>/.next/',
    '<rootDir>/dist/',
  ],

  // Performance
  maxWorkers: '50%',

  // Error handling
  errorOnDeprecated: true,
  verbose: true,
};
