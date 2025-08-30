/**
 * DRY Playwright base configuration - shared across all frontend apps
 * Eliminates duplication in E2E test setup
 */

import { defineConfig, devices } from '@playwright/test';
import path from 'path';

// DRY environment configuration
const isDevelopment = process.env.NODE_ENV === 'development';
const isCI = process.env.CI === 'true';

export default defineConfig({
  // Test directory patterns (can be overridden per app)
  testDir: './tests/e2e',

  // Global test configuration
  fullyParallel: true,
  forbidOnly: isCI, // Forbid test.only in CI
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'test-results/results.xml' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ...(isDevelopment ? [['list']] : [])
  ],

  // Global setup and teardown
  globalSetup: path.resolve(__dirname, 'setup/global-setup.js'),
  globalTeardown: path.resolve(__dirname, 'setup/global-teardown.js'),

  // DRY test configuration
  use: {
    // Base URL (can be overridden)
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',

    // Browser configuration
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Viewport
    viewport: { width: 1280, height: 720 },

    // Timeout configuration
    actionTimeout: 10000,
    navigationTimeout: 30000,

    // DRY authentication storage
    storageState: path.resolve(__dirname, 'storage/auth.json'),

    // Locale and timezone
    locale: 'en-US',
    timezoneId: 'America/New_York'
  },

  // DRY project configurations for different browsers and contexts
  projects: [
    // Setup project for authentication
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },

    // Desktop browsers
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Use auth from setup
        dependencies: ['setup']
      },
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        dependencies: ['setup']
      },
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        dependencies: ['setup']
      },
    },

    // Mobile browsers
    {
      name: 'Mobile Chrome',
      use: {
        ...devices['Pixel 5'],
        dependencies: ['setup']
      },
    },
    {
      name: 'Mobile Safari',
      use: {
        ...devices['iPhone 12'],
        dependencies: ['setup']
      },
    },

    // Tablet
    {
      name: 'iPad',
      use: {
        ...devices['iPad Pro'],
        dependencies: ['setup']
      },
    }
  ],

  // Development server configuration (DRY)
  webServer: {
    command: isDevelopment ? 'npm run dev' : 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !isCI,
    timeout: 120000,
  },

  // Output directories
  outputDir: 'test-results/',

  // Test timeout
  timeout: 30000,

  // Expect timeout
  expect: {
    timeout: 5000,
  },
});
