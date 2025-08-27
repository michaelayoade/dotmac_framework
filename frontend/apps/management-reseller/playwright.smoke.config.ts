import { defineConfig, devices } from '@playwright/test';

/**
 * Smoke test configuration - fast critical path tests
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e/smoke',
  
  /* Run tests in files in parallel for smoke tests */
  fullyParallel: true,
  
  /* Fail fast on smoke test failures */
  forbidOnly: !!process.env.CI,
  
  /* No retries for smoke tests - they should be stable */
  retries: 0,
  
  /* Use more workers for smoke tests (they're fast) */
  workers: process.env.CI ? 2 : 4,
  
  /* Reporter configuration for smoke tests */
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/smoke-results.json' }],
    ['junit', { outputFile: 'test-results/smoke-results.xml' }],
  ],
  
  /* Shared settings optimized for smoke tests */
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3004',
    
    /* Minimal tracing for smoke tests */
    trace: 'off',
    
    /* No screenshots for smoke tests (fast execution) */
    screenshot: 'off',
    
    /* No video for smoke tests */
    video: 'off',
    
    /* Faster timeouts for smoke tests */
    actionTimeout: 10000,
    navigationTimeout: 15000,
    
    /* Ignore HTTPS errors */
    ignoreHTTPSErrors: true,
    
    /* Minimal headers for smoke tests */
    extraHTTPHeaders: {
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
  },

  /* Minimal browser coverage for smoke tests */
  projects: [
    {
      name: 'chromium-smoke',
      use: { ...devices['Desktop Chrome'] },
    },
    
    /* Mobile smoke test */
    {
      name: 'mobile-smoke',
      use: { ...devices['Pixel 5'] },
    },
  ],

  /* No global setup for smoke tests - keep them fast */
  
  /* Run dev server for smoke tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3004',
    reuseExistingServer: !process.env.CI,
    timeout: 60000, // 1 minute - faster startup for smoke
  },

  /* Shorter timeout for smoke tests */
  timeout: 30000, // 30 seconds per smoke test

  /* Fast expectations */
  expect: {
    timeout: 5000, // 5 seconds for assertions
    threshold: 0.5, // More lenient for smoke tests
  },

  /* Minimal output for smoke tests */
  outputDir: 'test-results/smoke-artifacts',
  preserveOutput: 'failures-only',

  /* Metadata */
  metadata: {
    'test-type': 'smoke',
    'application': 'management-reseller',
    'environment': process.env.NODE_ENV || 'test',
    'purpose': 'Critical path validation',
  },
});