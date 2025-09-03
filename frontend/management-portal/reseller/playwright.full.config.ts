import { defineConfig, devices } from '@playwright/test';

/**
 * Full E2E test configuration - comprehensive testing
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry on CI for full E2E tests */
  retries: process.env.CI ? 2 : 1,

  /* Opt out of parallel tests on CI for stability */
  workers: process.env.CI ? 1 : 2,

  /* Comprehensive reporting for full E2E tests */
  reporter: [
    ['html', { outputFolder: 'test-results/e2e-report' }],
    ['json', { outputFile: 'test-results/e2e-results.json' }],
    ['junit', { outputFile: 'test-results/e2e-results.xml' }],
    ['github'], // GitHub Actions integration
  ],

  /* Comprehensive settings for full E2E testing */
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3004',

    /* Full tracing for comprehensive tests */
    trace: 'retain-on-failure',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video on failure for debugging */
    video: 'retain-on-failure',

    /* Standard timeouts */
    actionTimeout: 15000,
    navigationTimeout: 30000,

    /* Ignore HTTPS errors */
    ignoreHTTPSErrors: true,

    /* Full HTTP headers */
    extraHTTPHeaders: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.5',
      'Accept-Encoding': 'gzip, deflate',
      DNT: '1',
      Connection: 'keep-alive',
      'Upgrade-Insecure-Requests': '1',
    },

    /* Authentication state persistence */
    storageState: 'tests/e2e/auth/user.json',
  },

  /* Full browser matrix for comprehensive testing */
  projects: [
    /* Setup project for authentication */
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    /* Desktop browsers */
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },

    /* Mobile testing */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
    },

    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
      dependencies: ['setup'],
    },

    /* Branded browsers for compatibility */
    {
      name: 'Microsoft Edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
      dependencies: ['setup'],
    },

    {
      name: 'Google Chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chrome' },
      dependencies: ['setup'],
    },

    /* Accessibility testing */
    {
      name: 'accessibility',
      testDir: './tests/e2e/accessibility',
      use: {
        ...devices['Desktop Chrome'],
        // Enable accessibility features
        reducedMotion: 'reduce',
        forcedColors: 'active',
      },
      dependencies: ['setup'],
    },

    /* Performance testing */
    {
      name: 'performance',
      testDir: './tests/e2e/performance',
      use: {
        ...devices['Desktop Chrome'],
        // Performance testing specific settings
        launchOptions: {
          args: ['--no-sandbox', '--disable-dev-shm-usage'],
        },
      },
      dependencies: ['setup'],
    },
  ],

  /* Global setup and teardown */
  globalSetup: require.resolve('./tests/e2e/global-setup.ts'),
  globalTeardown: require.resolve('./tests/e2e/global-teardown.ts'),

  /* Run local dev server before starting tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3004',
    reuseExistingServer: !process.env.CI,
    timeout: 120000, // 2 minutes to start the dev server
  },

  /* Standard timeout for full E2E tests */
  timeout: 60000, // 1 minute per test

  /* Comprehensive expectations */
  expect: {
    timeout: 10000, // 10 seconds for assertions
    threshold: 0.2, // Strict visual comparison
    toHaveScreenshot: {
      threshold: 0.2,
      animations: 'disabled', // Consistent screenshots
    },
    toMatchSnapshot: {
      threshold: 0.2,
    },
  },

  /* Output configuration */
  outputDir: 'test-results/e2e-artifacts',
  preserveOutput: 'failures-only',

  /* Test metadata */
  metadata: {
    'test-type': 'end-to-end-full',
    application: 'management-reseller',
    environment: process.env.NODE_ENV || 'test',
    coverage: 'comprehensive',
    browsers: 'all-supported',
  },

  /* Test filtering */
  grep: process.env.E2E_GREP ? new RegExp(process.env.E2E_GREP) : undefined,
  grepInvert: process.env.E2E_GREP_INVERT ? new RegExp(process.env.E2E_GREP_INVERT) : undefined,
});
