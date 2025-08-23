/**
 * Simple Playwright configuration for demo tests
 */

import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: [
    '**/portal-demo.e2e.test.ts',
    '**/admin-portal-dashboard.e2e.test.ts',
    '**/admin-portal-customers.e2e.test.ts',
    '**/admin-login.e2e.test.ts',
    '**/admin-portal-billing.e2e.test.ts',
    '**/customer-portal-dashboard.e2e.test.ts',
  ],

  timeout: 30000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,

  reporter: [['html', { outputFolder: 'test-results/demo-report' }]],

  use: {
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10000,
  },

  projects: [
    {
      name: 'chromium-demo',
      use: {
        headless: true,
      },
    },
  ],

  outputDir: 'test-results/demo-output/',
});
