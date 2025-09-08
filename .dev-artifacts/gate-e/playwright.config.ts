/**
 * Playwright Configuration for Gate E: Full E2E + Observability Testing
 * Optimized for cross-service flow validation and observability testing
 */

import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const isCI = !!process.env.CI;
const isDev = process.env.NODE_ENV === 'development';

export default defineConfig({
  testDir: '.',
  outputDir: './test-results/artifacts',
  
  // Test execution settings - optimized for complex cross-service flows
  fullyParallel: !isCI, // Sequential in CI for stability
  forbidOnly: isCI,
  retries: isCI ? 2 : 1,
  workers: isCI ? 1 : 2, // Conservative for cross-service testing
  
  // Extended timeouts for complex E2E flows
  timeout: 180000, // 3 minutes per test
  expect: { 
    timeout: 30000, // 30 seconds for assertions
  },
  
  // Comprehensive reporting for Gate E validation
  reporter: [
    ['html', { 
      outputFolder: './test-results/gate-e-html-report',
      open: isDev ? 'on-failure' : 'never'
    }],
    ['json', { 
      outputFile: './test-results/gate-e-results.json' 
    }],
    ['junit', { 
      outputFile: './test-results/gate-e-results.xml' 
    }],
    // Custom Gate E reporter for observability validation
    ['line'],
    ...(isCI ? [['github']] : [])
  ],
  
  // Global test configuration
  use: {
    // Base URL for management platform
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://localhost:8000',
    
    // Comprehensive tracing for cross-service debugging
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Extended timeouts for cross-service operations
    actionTimeout: 20000,
    navigationTimeout: 45000,
    
    // Enhanced headers for observability
    extraHTTPHeaders: {
      'Accept': 'application/json, text/html',
      'X-Test-Environment': 'gate-e-validation',
      'X-Test-Type': 'cross-service-e2e',
      'X-Enable-Tracing': 'true',
      'X-Enable-Metrics': 'true'
    },
    
    // Browser settings
    ignoreHTTPSErrors: false,
    acceptDownloads: true,
    locale: 'en-US',
    timezoneId: 'America/New_York',
  },
  
  // Test projects for different aspects of Gate E
  projects: [
    // Setup project - prepares multi-service test environment
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
      use: { ...devices['Desktop Chrome'] }
    },
    
    // Main cross-service flow tests
    {
      name: 'cross-service-flows',
      testMatch: /cross-service-flow\.spec\.ts/,
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup']
    },
    
    // Observability-specific tests
    {
      name: 'observability-validation',
      testMatch: /.*observability.*\.spec\.ts/,
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup']
    },
    
    // Multi-browser testing for consistency
    {
      name: 'firefox-cross-service',
      testMatch: /cross-service-flow\.spec\.ts/,
      use: { 
        ...devices['Desktop Firefox'],
        // Reduced timeout for Firefox
        actionTimeout: 15000
      },
      dependencies: ['setup']
    },
    
    // Mobile testing for responsive cross-service flows
    {
      name: 'mobile-cross-service',
      testMatch: /cross-service-flow\.spec\.ts/,
      use: { 
        ...devices['iPhone 13']
        // Note: permissions handled within tests for v1.40.0 compatibility
      },
      dependencies: ['setup']
    },
    
    // Performance-focused tests
    {
      name: 'performance-validation',
      testMatch: /.*performance.*\.spec\.ts/,
      use: { 
        ...devices['Desktop Chrome'],
        // Performance testing specific settings
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1
      },
      dependencies: ['setup']
    },
    
    // Cleanup project
    {
      name: 'cleanup',
      testMatch: /.*\.teardown\.ts/,
      use: { ...devices['Desktop Chrome'] }
    }
  ],
  
  // Note: Backend services (management/isp) are started via Docker Compose
  // Only frontend services that need to be built are started here
  webServer: undefined, // Services managed by Docker Compose externally
  
  // Global setup and teardown for Gate E
  globalSetup: path.resolve(__dirname, 'setup/global-setup.ts'),
  globalTeardown: path.resolve(__dirname, 'setup/global-teardown.ts'),
  
  // Output configuration (v1.40.0 compatible)
  // preserveOutput: 'failures-only', // Not supported in v1.40.0
  
  // Gate E specific metadata
  metadata: {
    testType: 'gate-e-validation',
    environment: process.env.NODE_ENV || 'test',
    timestamp: new Date().toISOString(),
    gate: 'E',
    description: 'Full E2E + Observability Testing',
    services: [
      'dotmac-management',
      'isp-admin-frontend',
      'customer-portal', 
      'reseller-portal'
    ],
    testCategories: [
      'cross-service-flows',
      'observability-validation',
      'performance-testing',
      'multi-browser-testing'
    ]
  }
});