/**
 * Playwright E2E Testing Configuration
 * Following backend testing patterns for comprehensive E2E coverage
 */

import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests/e2e',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    process.env.CI ? ['github'] : ['list'],
  ],

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video on failure */
    video: 'retain-on-failure',

    /* Global timeout for each action */
    actionTimeout: 30000,

    /* Global timeout for navigation */
    navigationTimeout: 30000,
  },

  /* Configure projects for comprehensive browser testing */
  projects: [
    // Desktop Browsers - Latest Versions
    {
      name: 'Desktop Chrome Latest',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome',
        // Uncomment below for debugging
        // headless: false,
        // slowMo: 1000,
      },
    },
    {
      name: 'Desktop Chrome Beta',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome-beta',
      },
    },
    {
      name: 'Desktop Firefox Latest',
      use: { 
        ...devices['Desktop Firefox'],
        // Firefox-specific settings
        launchOptions: {
          firefoxUserPrefs: {
            'layout.css.devPixelsPerPx': '1.0',
          },
        },
      },
    },
    {
      name: 'Desktop Safari',
      use: { 
        ...devices['Desktop Safari'],
        // Safari-specific viewport
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: 'Microsoft Edge Latest',
      use: { 
        ...devices['Desktop Edge'], 
        channel: 'msedge',
        // Edge-specific settings
        launchOptions: {
          args: ['--disable-web-security', '--disable-features=VizDisplayCompositor'],
        },
      },
    },

    // Mobile Browsers - Latest iOS/Android
    {
      name: 'iPhone 14 Pro Safari',
      use: { 
        ...devices['iPhone 14 Pro'],
        // iOS-specific settings
        hasTouch: true,
        isMobile: true,
      },
    },
    {
      name: 'iPhone 13 Safari',
      use: { ...devices['iPhone 13'] },
    },
    {
      name: 'iPhone SE Safari',
      use: { ...devices['iPhone SE'] },
    },
    {
      name: 'Samsung Galaxy S22 Chrome',
      use: { 
        ...devices['Galaxy S8'],
        // Updated viewport for S22
        viewport: { width: 360, height: 780 },
        deviceScaleFactor: 3,
      },
    },
    {
      name: 'Pixel 7 Chrome',
      use: { 
        ...devices['Pixel 5'],
        // Updated for Pixel 7
        viewport: { width: 393, height: 851 },
        deviceScaleFactor: 2.75,
      },
    },

    // Tablet Viewports
    {
      name: 'iPad Pro 12.9"',
      use: { 
        ...devices['iPad Pro'],
        // Latest iPad Pro dimensions
        viewport: { width: 1024, height: 1366 },
      },
    },
    {
      name: 'iPad Air',
      use: { 
        browserName: 'webkit',
        viewport: { width: 820, height: 1180 },
        deviceScaleFactor: 2,
        hasTouch: true,
        isMobile: true,
      },
    },
    {
      name: 'Samsung Galaxy Tab',
      use: {
        browserName: 'chromium',
        viewport: { width: 800, height: 1280 },
        deviceScaleFactor: 1.5,
        hasTouch: true,
        isMobile: true,
      },
    },

    // Accessibility Testing Browsers
    {
      name: 'Chrome High Contrast',
      use: {
        ...devices['Desktop Chrome'],
        colorScheme: 'dark',
        reducedMotion: 'reduce',
        forcedColors: 'active',
        launchOptions: {
          args: [
            '--force-prefers-reduced-motion',
            '--enable-features=ForcedColors',
          ],
        },
      },
    },
    {
      name: 'Firefox Screen Reader Mode',
      use: {
        ...devices['Desktop Firefox'],
        // Screen reader simulation
        extraHTTPHeaders: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 NVDA/2021.1',
        },
      },
    },

    // Legacy Browser Support (if needed)
    {
      name: 'Chrome 100 Legacy',
      use: {
        ...devices['Desktop Chrome'],
        // Simulate older Chrome behavior
        launchOptions: {
          args: ['--disable-web-security', '--disable-features=VizDisplayCompositor'],
        },
        extraHTTPHeaders: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
        },
      },
    },

    // Network Conditions Testing
    {
      name: 'Chrome Slow 3G',
      use: {
        ...devices['Desktop Chrome'],
        // Simulate slow network
        launchOptions: {
          args: ['--simulate-slow-connection'],
        },
      },
    },
    {
      name: 'Mobile Slow Connection',
      use: {
        ...devices['Pixel 5'],
        // Simulate slow mobile connection
        networkProfile: {
          latency: 300,
          downloadThroughput: 125000, // 1 Mbps
          uploadThroughput: 62500,    // 0.5 Mbps
        },
      },
    },

    // Portal-specific Testing
    {
      name: 'Admin Portal Desktop',
      testMatch: '**/admin-portal*.test.*',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 }, // Common admin desktop size
      },
    },
    {
      name: 'Customer Portal Mobile',
      testMatch: '**/customer-portal*.test.*',
      use: {
        ...devices['iPhone 13'],
        // Customer portal optimized for mobile
      },
    },
    {
      name: 'Reseller Portal Tablet',
      testMatch: '**/reseller-portal*.test.*',
      use: {
        ...devices['iPad Pro'],
        // Reseller portal optimized for tablet
      },
    },
    {
      name: 'Technician Portal PWA',
      testMatch: '**/technician-portal*.test.*',
      use: {
        ...devices['Pixel 5'],
        // PWA-specific settings
        launchOptions: {
          args: ['--enable-features=WebAppInstallation'],
        },
      },
    },
  ],

  /* Global setup files */
  globalSetup: require.resolve('./tests/e2e/global-setup.ts'),
  globalTeardown: require.resolve('./tests/e2e/global-teardown.ts'),

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
  outputDir: 'test-results/',

  /* Test timeout */
  timeout: 60 * 1000,

  /* Expect timeout */
  expect: {
    timeout: 10 * 1000,
  },

  /* Test metadata */
  metadata: {
    framework: 'DotMac ISP Framework',
    version: '1.0.0',
  },
});
