/**
 * Playwright configuration for customer portal
 * Generated configuration - extends base config with portal-specific settings
 */

import { defineConfig } from '@playwright/test';
import baseConfig from '../../testing/e2e/playwright.config.base';

export default defineConfig({
  ...baseConfig,

  // Portal-specific test directory
  testDir: './tests/e2e',

  use: {
    ...baseConfig.use,
    baseURL: 'http://localhost:3001',
    storageState: './tests/e2e/auth-customer.json'
  },

  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3001',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },

  // Portal-specific projects
  projects: [
    // Setup for customer
    {
      name: 'customer-setup',
      testMatch: /.setup.ts/,
      use: {
        baseURL: 'http://localhost:3001',
      },
    },

    // Desktop tests
    {
      name: 'customer-chromium',
      dependencies: ['customer-setup'],
      use: {
        ...baseConfig.projects[1].use,
        baseURL: 'http://localhost:3001',
        storageState: './tests/e2e/auth-customer.json'
      },
    },


  ],
});
