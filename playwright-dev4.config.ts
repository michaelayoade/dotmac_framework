/**
 * Playwright Configuration for Dev 4 Integration Tests
 * 
 * Specialized configuration for management-tenant communication,
 * external integrations, and real-time system testing.
 */

import { defineConfig, devices } from '@playwright/test';
import { ciConfig, TestEnvironment } from './tests/config/ci.config';

export default defineConfig({
  // Test directory for Dev 4 integration tests
  testDir: './tests/e2e',
  testMatch: [
    'management-tenant-communication.spec.ts',
    'plugin-based-integrations.spec.ts',
    'realtime-systems.spec.ts'
  ],

  // Global setup for integration tests
  globalSetup: './tests/config/global-setup.ts',
  globalTeardown: './tests/config/global-teardown.ts',

  // Test execution settings
  fullyParallel: !ciConfig.useMockServices, // Sequential for mock services
  forbidOnly: !!process.env.CI,
  retries: ciConfig.retryAttempts,
  workers: ciConfig.parallelWorkers,
  timeout: ciConfig.testTimeout,

  // Reporting configuration
  reporter: process.env.CI ? [
    ['html', { outputFolder: 'test-results/playwright-report' }],
    ['junit', { outputFile: 'test-results/results.xml' }],
    ['json', { outputFile: 'test-results/results.json' }]
  ] : [
    ['html'],
    ['list']
  ],

  outputDir: 'test-results/artifacts',

  use: {
    // Base URL for management platform
    baseURL: ciConfig.mockEndpoints.managementApi,
    
    // Browser settings optimized for integration testing
    actionTimeout: 15000,
    navigationTimeout: 30000,
    
    // Capture screenshots and videos for debugging
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',

    // Headers for API testing
    extraHTTPHeaders: {
      'X-Test-Mode': 'true',
      'User-Agent': 'Playwright-E2E-Integration-Tests'
    }
  },

  // Project configurations for different test scenarios
  projects: [
    {
      name: 'management-tenant-communication',
      testMatch: 'management-tenant-communication.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        // Specific settings for management-tenant tests
        permissions: ['notifications'],
        timezoneId: 'America/New_York'
      }
    },
    
    {
      name: 'plugin-based-integrations',
      testMatch: 'plugin-based-integrations.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        // Settings for external API testing
        ignoreHTTPSErrors: process.env.NODE_ENV === 'test',
        extraHTTPHeaders: {
          'X-Test-Mode': 'true',
          'Authorization': `Bearer ${process.env.TEST_API_KEY || 'test_key_ci_12345'}`
        }
      }
    },
    
    {
      name: 'realtime-systems',
      testMatch: 'realtime-systems.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        // Settings for WebSocket testing
        permissions: ['notifications', 'microphone'],
        // Longer timeouts for real-time operations
        actionTimeout: 20000,
        navigationTimeout: 45000
      }
    },

    // Cross-browser testing for critical paths
    ...(process.env.CROSS_BROWSER_TEST === 'true' ? [
      {
        name: 'firefox-integration',
        testMatch: 'management-tenant-communication.spec.ts',
        use: {
          ...devices['Desktop Firefox'],
          permissions: ['notifications']
        }
      },
      
      {
        name: 'webkit-integration', 
        testMatch: 'realtime-systems.spec.ts',
        use: {
          ...devices['Desktop Safari'],
          permissions: ['notifications']
        }
      }
    ] : [])
  ],

  // Development server configuration
  webServer: ciConfig.useMockServices ? [
    {
      command: 'cd src && poetry run uvicorn dotmac_management.main:app --host 0.0.0.0 --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
      env: {
        DATABASE_URL: process.env.DATABASE_URL || 'postgresql://postgres:testpassword@localhost:5432/dotmac_test',
        REDIS_URL: process.env.REDIS_URL || 'redis://localhost:6379',
        TEST_MODE: 'true'
      }
    },
    {
      command: 'node tests/mock-servers/tenant-mock.js',
      port: 3100,
      reuseExistingServer: !process.env.CI,
      timeout: 30000
    }
  ] : undefined,

  // Test expectations and assertions
  expect: {
    // Increased timeout for external API calls
    timeout: 10000,
    
    // Custom matchers for integration testing
    toHaveScreenshot: {
      threshold: 0.3,
      mode: 'browser'
    }
  },

  // Metadata for test organization
  metadata: {
    testType: 'integration',
    developer: 'dev-4',
    coverage: ['management-tenant-communication', 'external-integrations', 'realtime-systems'],
    environment: process.env.NODE_ENV || 'test'
  }
});