import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for E2E Testing
 * Comprehensive configuration for cross-browser, mobile, and accessibility testing
 */

export default defineConfig({
  testDir: './tests/e2e',

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['html'],
    ['json', { outputFile: 'playwright-report/results.json' }],
    ['junit', { outputFile: 'playwright-report/junit.xml' }],
    process.env.CI ? ['github'] : ['list'],
  ],

  // Global timeout for each test
  timeout: 30000,

  // Global timeout for the whole test run
  globalTimeout: 10 * 60 * 1000, // 10 minutes

  // Shared settings for all tests
  use: {
    // Base URL to use in actions like `await page.goto('/')`
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://localhost:3000',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Take screenshots on failure
    screenshot: 'only-on-failure',

    // Record video for all tests
    video: process.env.CI ? 'retain-on-failure' : 'on-first-retry',

    // Accept downloads during testing
    acceptDownloads: true,

    // Ignore HTTPS errors
    ignoreHTTPSErrors: true,

    // Default navigation timeout
    navigationTimeout: 15000,

    // Default action timeout
    actionTimeout: 10000,
  },

  // Configure projects for major browsers and devices
  projects: [
    {
      name: 'chromium-desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },

    {
      name: 'firefox-desktop',
      use: {
        ...devices['Desktop Firefox'],
        viewport: { width: 1920, height: 1080 },
      },
    },

    {
      name: 'webkit-desktop',
      use: {
        ...devices['Desktop Safari'],
        viewport: { width: 1920, height: 1080 },
      },
    },

    // Mobile testing
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },

    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },

    // Tablet testing
    {
      name: 'tablet-chrome',
      use: { ...devices['Galaxy Tab S4'] },
    },

    {
      name: 'tablet-safari',
      use: { ...devices['iPad Pro'] },
    },

    // Technician portal PWA testing (mobile-focused)
    {
      name: 'technician-pwa-android',
      testMatch: '**/technician-portal.e2e.test.tsx',
      use: {
        ...devices['Pixel 5'],
        permissions: ['geolocation', 'camera', 'microphone'],
      },
    },

    {
      name: 'technician-pwa-ios',
      testMatch: '**/technician-portal.e2e.test.tsx',
      use: {
        ...devices['iPhone 13'],
        permissions: ['geolocation', 'camera', 'microphone'],
      },
    },

    // Admin portal testing (desktop-focused)
    {
      name: 'admin-portal-desktop',
      testMatch: '**/admin-portal.e2e.test.tsx',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },

    // Customer portal testing (responsive)
    {
      name: 'customer-portal-responsive',
      testMatch: '**/customer-portal.e2e.test.tsx',
      use: { ...devices['Desktop Chrome'] },
    },

    // Accessibility testing
    {
      name: 'accessibility-testing',
      use: {
        ...devices['Desktop Chrome'],
        // Enable accessibility tree in Chrome DevTools
        launchOptions: {
          args: ['--enable-accessibility-object-model'],
        },
      },
    },

    // Performance testing
    {
      name: 'performance-testing',
      use: {
        ...devices['Desktop Chrome'],
        // Enable performance metrics
        launchOptions: {
          args: ['--enable-blink-features=IdleDetection'],
        },
      },
    },

    // Security testing
    {
      name: 'security-testing',
      use: {
        ...devices['Desktop Chrome'],
        // Stricter security settings
        extraHTTPHeaders: {
          'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        },
      },
    },
  ],

  // Global setup and teardown
  globalSetup: require.resolve('./tests/e2e/global-setup.ts'),
  globalTeardown: require.resolve('./tests/e2e/global-teardown.ts'),

  // Run your local dev server before starting the tests
  webServer: [
    {
      command: 'pnpm run dev:admin',
      port: 3000,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: 'pnpm run dev:customer',
      port: 3001,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: 'pnpm run dev:technician',
      port: 3002,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],

  // Test metadata
  metadata: {
    'test-environment': process.env.NODE_ENV || 'development',
    'test-timestamp': new Date().toISOString(),
    'test-version': process.env.npm_package_version || '1.0.0',
  },

  // Expect options
  expect: {
    // Maximum time expect() should wait for the condition to be met
    timeout: 5000,

    // Custom matchers timeout
    toHaveScreenshot: { threshold: 0.3 },
    toMatchScreenshot: { threshold: 0.3 },
  },
});
