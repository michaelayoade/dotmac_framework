/**
 * Portal Visual Regression Testing Configuration
 * Specialized configuration for visual testing of portal components
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/portal-visualization.e2e.test.ts',

  /* Maximum time one test can run for. */
  timeout: 60 * 1000,

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : 2,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'test-results/portal-visual-report' }],
    ['json', { outputFile: 'test-results/portal-visual-results.json' }],
    process.env.CI ? ['github'] : ['list'],
  ],

  /* Shared settings for all the projects below. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',

    /* Collect trace when retrying the failed test. */
    trace: 'on-first-retry',

    /* Screenshot on failure and for visual tests */
    screenshot: 'only-on-failure',

    /* Video on failure */
    video: 'retain-on-failure',

    /* Global timeout for each action */
    actionTimeout: 15000,

    /* Global timeout for navigation */
    navigationTimeout: 30000,

    /* Visual comparison settings */
    ignoreHTTPSErrors: true,
  },

  /* Visual testing specific settings */
  expect: {
    /* Threshold for pixel differences in visual comparisons */
    toHaveScreenshot: {
      threshold: 0.4,
      maxDiffPixels: 1000,
      animationHandling: 'disable',
    },
    /* Default timeout for assertions */
    timeout: 10000,
  },

  /* Configure projects for major browsers and viewports */
  projects: [
    {
      name: 'Desktop Chrome - Portal Visuals',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
        // Always run headed for visual verification
        headless: !!process.env.CI,
      },
      testMatch: '**/portal-visualization.e2e.test.ts',
    },

    {
      name: 'Mobile Chrome - Portal Visuals',
      use: {
        ...devices['Pixel 5'],
        // Always run headed for visual verification
        headless: !!process.env.CI,
      },
      testMatch: '**/portal-visualization.e2e.test.ts',
      testIgnore: /.*@desktop.*/,
    },

    {
      name: 'Tablet iPad - Portal Visuals',
      use: {
        ...devices['iPad Pro'],
        // Always run headed for visual verification
        headless: !!process.env.CI,
      },
      testMatch: '**/portal-visualization.e2e.test.ts',
      testIgnore: /.*@mobile.*|.*@desktop.*/,
    },

    // High contrast testing
    {
      name: 'Accessibility - High Contrast',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
        colorScheme: 'dark',
        headless: !!process.env.CI,
      },
      testMatch: '**/*@a11y*',
    },
  ],

  /* Global setup files */
  globalSetup: require.resolve('./global-setup.ts'),
  globalTeardown: require.resolve('./global-teardown.ts'),

  /* Run your local dev server before starting the tests */
  webServer: process.env.CI
    ? undefined
    : {
        command: 'pnpm dev',
        port: 3000,
        reuseExistingServer: !process.env.CI,
        timeout: 120 * 1000,
      },

  /* Test output directory */
  outputDir: 'test-results/portal-visuals/',
});
